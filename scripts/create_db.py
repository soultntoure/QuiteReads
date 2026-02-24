"""Create the quitereads database if it doesn't exist."""

import asyncio
import asyncpg


async def create_database():
    """Create quitereads database."""
    try:
        # Connect to default 'postgres' database
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres",
        )

        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'quitereads'"
        )

        if exists:
            print("Database 'quitereads' already exists.")
        else:
            # Create database (can't use prepared statements for CREATE DATABASE)
            await conn.execute("CREATE DATABASE quitereads")
            print("Database 'quitereads' created successfully.")

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_database())
