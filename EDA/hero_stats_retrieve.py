# Import necessary dependencies
import re
import sys
from requests import get
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict
import seaborn as sns

pd.set_option("display.max_columns", 300)

def _get_current_hero_stats(
        api_link: str = "https://api.opendota.com/api/heroStats"
) -> List[Dict]:
    """
    Get stats about all heroes' performance in recent matches from 'https://api.opendota.com/api/heroStats' or 
    from the different API specifed in `api_link`.

    Parameters
    ----------
    api_link: str
        Link to the API where requests should be sent.
    Returns
    ----------
    response: list[dict]
        The list containing statistics about all heroes' performance in recent matches. 
        [Output format description](https://docs.opendota.com/#tag/hero-stats/operation/get_hero_stats).
    """

    response = get(api_link)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve data, status code: {response.status_code}")
        return []

def _format_names_and_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle names format and missing values.

    Parameters
    ----------
    df: pd.DataFrame
        The dataframe that were created using `get_current_hero_stats`.
    
    Returns
    ----------
    pd.DataFrame
        Preprocessed dataframe with no missing values & proper names format.
    """

    heroes_df = df.copy()

    # Transform all hero names in appropriate format
    heroes_df["name"] = heroes_df.loc[:, "name"].apply(lambda x: "_".join(x.split("_")[3:]))

    # Fill missing health regen value for undying
    heroes_df["base_health_regen"] = heroes_df.loc[:, "base_health_regen"].fillna(-0.25)

    # Drop turn rate due to large absence of values
    heroes_df = heroes_df.drop(labels=["turn_rate"], axis=1)

    if int(heroes_df.isna().sum().sum()) > 0:
        heroes_df = heroes_df.fillna(0.0)
    
    return heroes_df

def retrieve_stats(
    api_link: str = "https://api.opendota.com/api/heroStats"
) -> pd.DataFrame:
    """
    Acquire & return dataset with each heroes' characteristics & statistics.

    Parameters
    ----------
    api_link: str
        Link to the API that return stats about all heroes' performance in recent matches from 'https://api.opendota.com/api/heroStats' or 
        from the different API specifed in `api_link`.
    
    Returns
    ----------
    pd.DataFrame
        Heroes' characteristics & statistics.
    """

    df = pd.DataFrame(_get_current_hero_stats(api_link=api_link)).set_index("id")

    formatted_df = _format_names_and_missing(df=df)

    return formatted_df

if __name__ == "__main__":

    if len(sys.argv) == 1:
        # No arguments provided - use default API and print to stdout
        print(retrieve_stats().to_csv())
    elif len(sys.argv) == 2:
        # One argument provided - treat as output file path
        retrieve_stats().to_csv(sys.argv[1])
    elif len(sys.argv) == 3:
        # Two arguments provided - treat as API link and output file path
        retrieve_stats(api_link=sys.argv[1]).to_csv(sys.argv[2])
    else:
        raise Exception("Incorrect command line arguments format.\n"
                      "Usage:\n"
                      "python script.py [output_file_path]\n"
                      "or\n"
                      "python script.py [api_link] [output_file_path]")