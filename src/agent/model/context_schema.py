from dataclasses import dataclass


@dataclass
class ContextSchema:
    sender_name: str
    sender_type: str
    receiver_name: str
