from datetime import datetime as dt
from enum import Enum
from random import Random, randrange
# from typing import TypeVar
import csv

import pandas as pd

# Define generic type, used for type hinting only
# T = TypeVar("T")


### UPDATE AS NEEDED
CUR_YEAR = 2025
DATES = ["Nov 24", "Nov 25", "Nov 26", "Nov 27"]
### UPDATE AS NEEDED


def to_timestr(timestamp: dt) -> str:
	"""Converts a datetime object into a human-readable format."""
	return timestamp.strftime("%a %b %d @ %I:%M %p").replace(" 0", " ")


class Location(Enum):
	"""Represents the geographic location shared between a Delegate and a
	Parliamentarian."""
	Local = 0
	Constituency = 1
	Province = 2
	Any = 3


class Priority(Enum):
	"""Orders the needs of a Parliamentarian given the candidate Delegates
	already assigned to them."""
	Satisfied = 0
	Unsatisfied = 1
	Unsat_req_prov = 2
	Unsat_req_const = 3
	Unsat_req_local = 4


class Delegate:
	def __init__(self, deleg_row: pd.DataFrame) -> None:
		self.name: str = deleg_row.at["Name"]
		self.email: str = deleg_row.at["Email"]
		self.avail: dict[str, bool] = {date: deleg_row.at[date] for date in DATES}
		self.staff: bool = deleg_row.at["Staff?"]
		self.local: int | None = deleg_row.at["Local #"]
		self.constituency: str = deleg_row.at["Constituency Name"]
		self.province: str = deleg_row.at["Province Name"]
		self.assigned: list[str] = []
		self.backup: list[str] = []
	
	def write(self) -> str:
		outstrs = [self.name]
		if not self.assigned and not self.backup:
			outstrs.append("  Not assigned to any parliamentarian")
		if self.assigned:
			outstrs.append(f"  Assigned to: ({len(self.assigned)})")
			for parl in self.assigned:
				outstrs.append(f"    {parl}")
		if self.backup:
			outstrs.append(f"  Backup for: ({len(self.backup)})")
			for parl in self.backup:
				outstrs.append(f"    {parl}")
		return '\n'.join(outstrs)


class Parliamentarian:
	def __init__(self, parl_row: pd.DataFrame) -> None:
		self.role: str = parl_row.at["MP/Sen"]
		self.name: str = parl_row.at["Name"]
		self.email: str = parl_row.at["Email"]
		self.constituency: str | None = parl_row.at["Constituency"]
		self.province: str = parl_row.at["Province / Territory"]
		self.req_local: list[int] = [
			int(num)
			for num in str(parl_row["Requires Local (#)"]).split(",")
			if num != "nan"
		]
		self.req_const: bool = parl_row.at["Requires Constituent?"]
		self.req_prov: bool = parl_row.at["Requires province-dweller?"]
		self.timeslot: dt | None = parl_row.at["timestamp"]
		self.date_label: str = parl_row.at["date_label"]
		self.candidates: dict[str, list[Delegate]] = {l.name: [] for l in Location}
		self.assigned: list[tuple[Delegate, Location]] = []
		self.backup: list[tuple[Delegate, Location]] = []
		self.staff: list[tuple[Delegate, Location]] = []
	
	def add_delegate(self, deleg: Delegate, score: float) -> None:
		enum_value: int = len(Location) - int(score) - 1
		self.candidates[Location(enum_value).name].append(deleg)
	
	def num_candidates(self, match_type: Location = Location.Any) -> int:
		num = 0
		for loc in Location:
			num += len(self.candidates[loc.name])
			if match_type == loc:
				return num
	
	def get_priority(self, thresh: int = 2) -> Priority:
		if self.req_local and self.num_candidates(Location.Local) < thresh:
			return Priority.Unsat_req_local
		elif self.req_const and self.num_candidates(Location.Constituency) < thresh:
			return Priority.Unsat_req_const
		elif self.req_prov and self.num_candidates(Location.Province) < thresh:
			return Priority.Unsat_req_prov
		elif self.num_candidates(Location.Any) < thresh:
			return Priority.Unsatisfied
		return Priority.Satisfied
	
	def score_quality(self, deleg: Delegate) -> float:
		# Assumes the delegate is available to meet the parliamentarian
		# Set fractional quality based on Parliamentarian need
		score = self.get_priority().value / len(Priority)
		# Set integral quality based on match quality
		if self.req_local and deleg.local in self.req_local:
			score += 3
		elif self.constituency and self.constituency == deleg.constituency:
			score += 2
		elif self.province == deleg.province:
			score += 1
		return score
	
	def assign_delegates(self) -> None:
		delegs = [
			(deleg, l.value, len(deleg.assigned), len(deleg.backup))
			for l in Location
			for deleg in self.candidates[l.name]
		]
		delegs.sort(key=lambda x: x[1:])
		if self.get_priority(thresh=1) != Priority.Satisfied:
			return
		for deleg, loc, *_ in delegs[:4]:
			if len(self.assigned) < 2:
				self.assigned.append((deleg, Location(loc)))
				deleg.assigned.append(f"{self.name} ({to_timestr(self.timeslot)})")
			else:
				self.backup.append((deleg, Location(loc)))
				deleg.backup.append(f"{self.name} ({to_timestr(self.timeslot)})")
	
	def get_contact_info(self) -> tuple[str, ...]:
		output = []
		# Add self
		output.extend([self.name, self.email])
		# Add assigned delegates
		for i in range(2):
			try:
				deleg = self.assigned[i][0]
				output.extend([deleg.name, deleg.email])
			except (IndexError, AttributeError):
				output.extend(["None", "None"])
		# Add backup delegates
		for i in range(2):
			try:
				deleg = self.backup[i][0]
				output.extend([deleg.name, deleg.email])
			except (IndexError, AttributeError):
				output.extend(["None", "None"])
		# Add staff
		try:
			deleg = self.staff[0][0]
			output.extend([deleg.name, deleg.email])
		except (IndexError, AttributeError):
			output.extend(["None", "None"])
		
		return tuple(output)


	def write(self) -> str:
		outstrs = []
		reqs = ""
		if self.req_local:
			reqs = "Requires delegate from a represented Local"
		elif self.req_const:
			reqs = "Requires delegate from the same Constituency"
		elif self.req_prov:
			reqs = "Requires delegate from the same Province"
		
		if self.get_priority(thresh=1) != Priority.Satisfied:
			outstrs.append(f"{self.name}: Requirements Not Met!")
			outstrs.append(reqs)
		else:
			outstrs.append(f"{self.name} - {self.num_candidates()} available candidates")
			if reqs:
				outstrs.append(reqs)
			# Write selected delegates
			outstrs.append(f"  Delegates:")
			for deleg, loc in self.assigned:
				outstrs.append(f"    {deleg.name} - ({loc.name})")
			# Write backup delegates
			outstrs.append(f"  Backups:")
			for deleg, loc in self.backup:
				outstrs.append(f"    {deleg.name} - ({loc.name})")
		return '\n'.join(outstrs)


class Matchmaker:
	def __init__(self, parl_file: str, deleg_file: str, seed: int = 0) -> None:
		# Sample RNG seeding (missing some type hints)
		if seed == 0:
			self.seed: int = randrange(2**31-1)
		else:
			self.seed: int = seed
		self.rng = Random(self.seed)
		
		# Read from CSV files
		deleg_data = pd.read_csv(deleg_file, encoding="utf-8")
		parl_data = pd.read_csv(parl_file, encoding="utf-8")

		# Remove delegate rows without names
		deleg_data.dropna(subset=["Name"], inplace=True, ignore_index=True)

		# Keep only delegate rows not marked as rejected (e.g. duplicates)
		deleg_data = deleg_data.loc[deleg_data["Reject?"] == False]

		# Select only relevant delegate columns
		deleg_data = deleg_data[[
			"Name", "Languages", "Local #", "Full Name", "Staff?", "Email",
			"Constituency Name", "Province Name"
		] + DATES]

		# Remove MP/Sen rows without names
		parl_data.dropna(subset=["Name"], inplace=True, ignore_index=True)

		# Select only MP/Sen who are attending
		parl_data = parl_data.loc[parl_data["Attending?"] == True]
		parl_data.reset_index(drop=True, inplace=True)

		# Convert timeslot into datetime object
		parl_data["timestamp"] = pd.to_datetime(
			parl_data["Start Time"],
			errors="coerce",
			format="%b %d, %Y, %H:%M",
		)

		# Add date label
		parl_data["date_label"] = parl_data["timestamp"].dt.strftime("%b %d")

		# Create, randomize, and store Delegates {name: Delegate}
		nrows = len(deleg_data)
		deleg_data.index = self.rng.sample(range(nrows), k=nrows)
		deleg_data.sort_index(inplace=True)
		self.deleg = {
			row.at["Name"]: Delegate(row)
			for idx, row in deleg_data.iterrows()
		}

		# Create and store Parliamentarians {name: Parliamentarian}
		self.parl = {
			row.at["Name"]: Parliamentarian(row)
			for idx, row in parl_data.iterrows()
		}

		# Determine, sort, and store meeting timeslots
		self.timeslots = {
			timeslot: parl_data.loc[parl_data["timestamp"] == timeslot]["Name"].to_list()
			for timeslot in sorted(parl_data["timestamp"].unique())
			if not pd.isnull(timeslot)
		}
		self.timeslots[pd.NaT] = parl_data.loc[parl_data["timestamp"].isnull()]["Name"].to_list()
	
	def run(self) -> str:
		# Iterate over timeslots, assigning delegates to parliamentarians
		# Check for delegate availability
		for timeslot, parl_name_list in self.timeslots.items():
			# Skip if timeslot not assigned
			if pd.isnull(timeslot):
				continue
			date_label = self.parl[parl_name_list[0]].date_label
			for deleg in self.deleg.values():
				# Skip if not available
				if not deleg.avail[date_label]:
					continue
				# Allocate delegate to one of the parls in the timeslot
				scores = {
					parl_name: self.parl[parl_name].score_quality(deleg)
					for parl_name in parl_name_list
				}
				top_score = max(scores.values())
				selected_parl = self.rng.choice([
					parl_name
					for parl_name, score in scores.items()
					if score == top_score
				])
				self.parl[selected_parl].add_delegate(deleg, top_score)
		# Select delegates out of assigned groupings
		parl_list = [(parl, parl.num_candidates()) for _, parl in self.parl.items()]
		parl_list.sort(key=lambda x: x[1])
		for row in parl_list:
			parl, _ = row
			parl.assign_delegates()
	
	def write(self) -> str:
		outstrs = []
		outcsv = [(
			"Timeslot", "MP/Sen Name", "MP/Sen Email", "Delegate 1", "Delegate 1 Email",
			"Delegate 2", "Delegate 2 Email", "Backup 1", "Backup 1 Email",
			"Backup 2", "Backup 2 Email", "Staff", "Staff Email"
		)]
		outstrs.append(f"Random seed: {self.seed}\n")
		outstrs.append("=" * 80 + "\n")
		for timeslot, parl_name_list in self.timeslots.items():
			# Timeslot not assigned
			if pd.isnull(timeslot):
				outstrs.append(f"Timeslot not assigned - ({len(parl_name_list)})")
				for parl_name in parl_name_list:
					outstrs.append(f"  {parl_name}")
				continue
			# Timeslot assigned
			outstrs.append(f"{to_timestr(timeslot)} - ({len(parl_name_list)})")
			for parl_name in parl_name_list:
				outstrs.append(self.parl[parl_name].write() + "\n")
			# Add row to csv
			for parl_name in parl_name_list:
				parl = self.parl[parl_name]
				outcsv.append([timeslot, *parl.get_contact_info()])

		outstrs.append("\n" + "=" * 80 + "\n")

		for deleg in self.deleg.values():
			outstrs.append(deleg.write() + "\n")
		
		filename = f"output_{dt.now().strftime('%Y%m%d_%H%M%S')}"
		with open(filename + ".txt", "w", encoding="utf-8") as f1:
			f1.write("\n".join(outstrs))
		with open(filename + ".csv", "w", newline="", encoding="utf-8") as f2:
			csv.writer(f2).writerows(outcsv)


if __name__ == "__main__":
	mm = Matchmaker(
		parl_file="Database for Matchmaking - MP_Sen Data.csv",
		deleg_file="Database for Matchmaking - Del Data.csv"
	)
	mm.run()
	mm.write()