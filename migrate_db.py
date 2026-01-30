import pandas as pd


CSV_PATH = "Nesta Signal Vault - Sheet1.csv"


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "Score_Impact" not in df.columns:
        df["Score_Impact"] = 0
    if "Analysis" not in df.columns:
        df["Analysis"] = ""
    if "Implication" not in df.columns:
        df["Implication"] = ""
    return df


def migrate_csv(csv_path: str = CSV_PATH) -> None:
    df = pd.read_csv(csv_path)
    df = ensure_columns(df)
    df.to_csv(csv_path, index=False)


if __name__ == "__main__":
    migrate_csv()
