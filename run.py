if __name__ in {"__main__", "__mp_main__"}:
    import dotenv
    dotenv.load_dotenv()

    from app import start_web_server
    start_web_server()
