import argparse
import asyncio
import logging

from zappai import logging_conf
from zappai.database.di import get_session_maker
from zappai.users.di import get_user_repository

async def main():
    # Create the ArgumentParser object
    parser = argparse.ArgumentParser(
        description="Create a user"
    )

    # Add the file path argument
    parser.add_argument("--username", type=str, required=True)
    parser.add_argument("--password", type=str, required=True)
    parser.add_argument("--name", type=str, required=True)
    parser.add_argument("--email", type=str)

    args = parser.parse_args()

    user_repository = get_user_repository()
    session_maker = get_session_maker()

    async with session_maker() as session:
        await user_repository.create_user(session=session, username=args.username, password=args.password, name=args.name, email=args.email)
        await session.commit()
    
    print(f"User {args.username} created!")

if __name__ == "__main__":
    logging_conf.create_logger(config=logging_conf.get_default_conf())
    asyncio.run(main())