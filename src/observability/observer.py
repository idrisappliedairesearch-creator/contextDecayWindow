from src.observability.file_writer import FileWriter
from src.observability.run_config import RunConfig
from src.observability.terminal import TerminalPrinter
from src.observability.turn_record import TurnRecord


class Observer:

    def __init__(self, config: RunConfig):
        self.config = config
        self.terminal = TerminalPrinter()
        self.file_writer = FileWriter(config)

    def init_run(self) -> None:
        self.file_writer.init_run()

    def flush_turn(self, record: TurnRecord) -> None:
        self.terminal.print_turn(record)
        self.file_writer.write_turn(record)
