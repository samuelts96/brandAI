from bookkeeper_test_connection import bookkeeper
import asyncio


response=asyncio.run(bookkeeper("atlanta.csv","What was the average temperature of 1985?"))