import pandas as pd
from datetime import datetime as dt


def matchmake() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Given two CSV files for delegate and MP/senator data (proprietary
    format), create a file with the schedule and details for meetings.    
    """
    ### ======= Load data from file =======

    # Read from CSV files
    del_data = pd.read_csv("Database for Matchmaking - Del Data.csv")
    mp_sen_data = pd.read_csv("Database for Matchmaking - MP_Sen Data.csv")

    # Remove delegate rows without names
    del_data.dropna(subset=["Name"], inplace=True, ignore_index=True)

    # Remove delegate rows marked as rejected (e.g. duplicates)
    del_data = del_data.loc[del_data["Reject?"] == True]

    # Select only relevant delegate columns
    del_data = del_data[[
        "Name", "Languages", "Nov 24", "Nov 25", "Nov 26", "Nov 27",
        "Local #", "Full Name", "Staff?", "Constituency Name", "Province Name"
    ]]

    # Remove MP/Sen rows without names
    mp_sen_data.dropna(subset=["Name"], inplace=True, ignore_index=True)

    # Select only MP/Sen who are attending
    mp_sen_data = mp_sen_data.loc[mp_sen_data["Attending?"] == True]
    mp_sen_data.reset_index(drop=True, inplace=True)

    # Convert timeslot into datetime object
    mp_sen_data["timestamp"] = pd.to_datetime(
        mp_sen_data["Start Time"],
        errors="coerce",
        format="%b %d, %Y, %H:%M",
    )

    # print(mp_sen_data)

    ### ======= Find delegate fit quality =======

    # These are what we care about for match quality
    priority = ["local", "constituency", "province"]

    # For each timeslot, create a list of MP/Sen at that time
    timeslots = {
        timeslot: {
            mpsen: {prio: [] for prio in priority}
            for mpsen in mp_sen_data.loc[mp_sen_data["timestamp"] == timeslot]["Name"].to_list()
        }
        for timeslot in sorted(mp_sen_data["timestamp"].unique())
        if str(timeslot) != "NaT"
    }
    for k, v in timeslots.items():
        print(f"key: {k}\nvalue: {v}")

    def mpsen_by_need(mpsen_list):
        nonlocal timeslots
        pass

    # Assign students to appropriate buckets (one per timeslot)
    for timeslot, persons in timeslots.items():
        # Find date and format like column label
        date = timeslot.strftime("%b %d").replace(" 0", " ")
        for delegate_row in del_data.loc[del_data[date] == True]:
            # Score table: lower score is more preferable/better match
            scores = {mpsen_name: float("inf") for mpsen_name in persons}
            for mpsen_name in persons:
                mpsen_row = mp_sen_data.loc[mp_sen_data["Name"] == mpsen_name]
                print(mpsen_row)
                # Check if MP/Sen requires a local
                if local := mpsen_row["Requires Local (#)"]:
                    if local.find(delegate_row["Local $"]) >= 0:
                        scores[mpsen_name] = 0
                        break
                # Check for constituency and province match
                if mpsen_row["Constituency"] and mpsen_row["Constituency"] == delegate_row["Constituency Name"]:
                    scores[mpsen_name] = 1
                elif mpsen_row["Province / Territory"] == delegate_row["Province Name"]:
                    scores[mpsen_name] = 2
            # Assign to buckets based on score
            # Remove from any MP/Sen where this delegate has a better match
            candidate_mpsen = [
                k for k, v in scores.items()
                if v == min(scores.values())
            ]
            return
    #   Student must be available
    # Assign staff if available



if __name__ == "__main__":
    matchmake()
