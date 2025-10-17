from datetime import datetime as dt
from enum import Enum
from random import Random, randrange
from typing import Callable, Dict, List, Sequence, TypeVar

import pandas as pd

# Define generic type, used for type hinting only
T = TypeVar("T")


### UPDATE AS NEEDED
CUR_YEAR = 2025
DATES = ["Nov 24", "Nov 25", "Nov 26", "Nov 27"]


class Location(Enum):
	Local = 0
	Constituency = 1
	Province = 2


class Priority(Enum):
	Satisfied = 0
	Unsatisfied = 1
	Unsat_req_prov = 2
	Unsat_req_const = 3
	Unsat_req_local = 4


class Delegate:
	def __init__(self, deleg_row: pd.DataFrame, select_fn: Callable[[Sequence[T]], T]) -> None:
		self.name: str = deleg_row.at["Name"]
		self.avail: Dict[str, bool] = {date: deleg_row.at[date] for date in DATES}
		self.staff: bool = deleg_row.at["Staff?"]
		self.local: int | None = deleg_row.at["Local #"]
		self.constituency: str = deleg_row.at["Constituency Name"]
		self.province: str = deleg_row.at["Province Name"]
		self.select: Callable[[Sequence[T]], T] = select_fn
	
	def assign(self, parl_list: List["Parliamentarian"]) -> None:
		scores = {i: parl_list[i].score_quality(self) for i in range(len(parl_list))}
		top_score = max(scores.values())
		selection = self.select([i for i, score in scores.items() if score == top_score])
		# Assign to parl
		parl_list[selection].add_delegate(self, top_score)


class Parliamentarian:
	def __init__(self, parl_row: pd.DataFrame) -> None:
		self.role: str = parl_row.at["MP/Sen"]
		self.name: str = parl_row.at["Name"]
		self.constituency: str | None = parl_row.at["Constituency"]
		self.province: str = parl_row.at["Province / Territory"]
		self.req_local: List[int] = [
			int(num)
			for num in str(parl_row["Requires Local (#)"]).split(",")
			if num != "nan"
		]
		self.req_const: bool = parl_row.at["Requires Constituent?"]
		self.req_prov: bool = parl_row.at["Requires province-dweller?"]
		self.timeslot: dt | None = parl_row.at["timestamp"]
		self.date_label: str = parl_row.at["date_label"]
		self.candidates: Dict[str, List[str]] = {k.name: [] for k in Location}
	
	def add_delegate(self, delegate: Delegate, score: float) -> None:
		if score > 0:
			enum_value: int = int(len(Location) - score)
			self.candidates[Location(enum_value).name].append(delegate.name)
	
	def num_candidates(self, match_type: Location | None) -> int:
		num = 0
		for loc in Location:
			num += len(self.candidates[loc.name])
			if match_type is not None and match_type == loc:
				return num
		return num
	
	def get_priority(self) -> Priority:
		if self.req_local and self.num_candidates(Location.Local) < 2:
			return Priority.Unsat_req_local
		elif self.req_const and self.num_candidates(Location.Constituency) < 2:
			return Priority.Unsat_req_const
		elif self.req_prov and self.num_candidates(Location.Province) < 2:
			return Priority.Unsat_req_prov
		elif self.num_candidates(None) < 2:
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
	
	def write(self) -> str:
		outstrs = []
		if self.get_priority().value > 0:
			outstrs.append(f"{self.name}: Requirements Not Met!")
		else:
			delegs = [
				deleg
				for deleg_list in self.candidates.values()
				for deleg in deleg_list
			]
			outstrs.append(f"{self.name} - {len(delegs)} available candidates")
			# Write selected delegates
			outstrs.append(f"  Delegates:")
			for deleg in delegs[:2]:
				outstrs.append(f"    {deleg}")
			# Write backup delegates
			if len(delegs) > 2:
				outstrs.append(f"  Backups:")
				for deleg in delegs[2:4]:
					outstrs.append(f"    {deleg}")
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
		deleg_data = pd.read_csv(deleg_file)
		parl_data = pd.read_csv(parl_file)

		# Remove delegate rows without names
		deleg_data.dropna(subset=["Name"], inplace=True, ignore_index=True)

		# Keep only delegate rows not marked as rejected (e.g. duplicates)
		deleg_data = deleg_data.loc[deleg_data["Reject?"] == False]

		# Select only relevant delegate columns
		deleg_data = deleg_data[[
			"Name", "Languages", "Local #", "Full Name", "Staff?",
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
			row.at["Name"]: Delegate(row, self.rng.choice)
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
			parl_list = [self.parl[name] for name in parl_name_list]
			for deleg_name, deleg in self.deleg.items():
				# Skip if not available
				if not deleg.avail[date_label]:
					continue
				deleg.assign(parl_list)

	
	def write(self) -> str:
		outstrs = []
		outstrs.append(f"Random seed: {self.seed}\n")
		for timeslot, parl_name_list in self.timeslots.items():
			# Timeslot not assigned
			if pd.isnull(timeslot):
				outstrs.append(f"Timeslot not assigned - ({len(parl_name_list)})")
				for parl_name in parl_name_list:
					outstrs.append(f"  {parl_name}")
				continue
			# Timeslot assigned
			outstrs.append(f"{timeslot} - ({len(parl_name_list)})")
			for parl_name in parl_name_list:
				outstrs.append(self.parl[parl_name].write())
			outstrs.append("")
		
		filename = f"output_{dt.now().strftime('%Y%m%d_%H%M%S')}.txt"
		with open(filename, 'w') as f:
			f.write('\n'.join(outstrs))


if __name__ == "__main__":
	mm = Matchmaker(
		parl_file="Database for Matchmaking - MP_Sen Data.csv",
		deleg_file="Database for Matchmaking - Del Data.csv"
	)
	mm.run()
	mm.write()