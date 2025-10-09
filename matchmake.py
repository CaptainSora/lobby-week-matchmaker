import pandas as pd


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Read from CSV files
    del_data = pd.read_csv("Database for Matchmaking - Del Data.csv")
    mp_sen_data = pd.read_csv("Database for Matchmaking - MP_Sen Data.csv")

    # Remove delegate rows without names
    del_data.dropna(subset=["Name"], inplace=True, ignore_index=True)

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

    print(del_data)

    return del_data, mp_sen_data


if __name__ == "__main__":
    load_data()
