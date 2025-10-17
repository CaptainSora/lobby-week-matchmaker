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
	def __init__(self, deleg_row: pd.Dataframe, select_fn: Callable[[Sequence[T]], T]) -> None:
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
	def __init__(self, parl_row: pd.Dataframe) -> None:
		self.role: str = parl_row.at["MP/Sen"]
		self.name: str = parl_row.at["Name"]
		self.constituency: str | None = parl_row.at["Constituency"]
		self.province: str = parl_row.at["Province / Territory"]
		self.req_local: List[int] = [int(num) for num in parl_row["Requires Local (#)"].split(",")]
		self.req_const: bool = parl_row.at["Requires Constituent?"]
		self.req_prov: bool = parl_row.at["Requires province-dweller?"]
		self.timeslot: dt | None = parl_row.at["timestamp"]
		self.candidates: Dict[str, List[str]] = {k.name: [] for k in Location}
	
	def add_delegate(self, delegate: Delegate, score: float) -> None:
		enum_value: int = len(Location) - int(score)
		self.candidates[Location[enum_value].name].append(delegate.name)
	
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
	
	def output(self) -> str:
		pass


class Matchmaker:
	def __init__(self, parl_file: str, deleg_file: str, seed: int = 0) -> None:
		# Sample RNG seeding (missing some type hints)
		if seed == 0:
			self.seed: int = randrange(2**31-1)
		else:
			self.seed: int = seed
		self.rng = Random(seed)
		# Insert load and parse here
		parl_data = ...
		deleg_data = ...
		# Create and store Parliamentarians {name: Parliamentarian}
		self.parl = ...
		# Create, randomize, and store Delegates {name: Delegate}
		self.deleg = ...
		# ... select_fn = self.rng.choice)
		# Determine, sort, and store meeting timeslots
		self.timeslots = {
			timeslot: parl_data.loc[parl_data["timestamp"] == timeslot]["Name"].to_list()
			for timeslot in sorted(self.parl["timestamp"].unique())
		}
		pass
	
	def run(self) -> str:
		# Iterate over timeslots, assigning delegates to parliamentarians
		# Check for delegate availability
		for timeslot, parl_name in self.timeslots.items():
			pass
	
	def output(self) -> str:
		pass
