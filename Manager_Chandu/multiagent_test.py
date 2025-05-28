
if __name__ == "__main__":
    async def main():
        print("Manager Agent Ready.")
        print("Type 'exit' to quit or 'reset' to clear cache.\n")

        while True:
            query = input("Enter your query (or 'reset'): ").strip()
            if query.lower() in {"exit", "quit"}:
                print("Exiting.")
                break
            if query.lower() == "reset":
                reset_session_cache()
                last_pdf_path["value"] = None
                continue

            path = input("Enter file path (or leave blank): ").strip()
            if path.lower() == "reset":
                reset_session_cache()
                last_pdf_path["value"] = None
                continue

            path = path if path else None
            output = await run_manager_agent(query=query, path=path)

            print("\nResult:\n", output)
            print("\n" + "-" * 60 + "\n")
    asyncio.run(main())
