from pathlib import Path

from recallcode.database import Base, engine


def main() -> None:
    Path("data").mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print("RecallCode database initialized successfully.")


if __name__ == "__main__":
    main()
