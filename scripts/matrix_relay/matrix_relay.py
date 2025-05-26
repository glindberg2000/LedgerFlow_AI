#!/usr/bin/env python3
"""
Matrix Relay - Connects Cursor terminal to Matrix server for AI communication
"""
import os
import sys
import json
import time
import argparse
import requests
import threading
from datetime import datetime

# Configuration
DEFAULT_HOMESERVER = "http://localhost:8008"
DEFAULT_ROOM_ID = None  # Will create a room if None
DEFAULT_USER = "cursor_ai"
DEFAULT_PASSWORD = "cursor_ai_password"


class MatrixRelay:
    def __init__(self, homeserver, username, password, room_id=None):
        self.homeserver = homeserver
        self.username = username
        self.password = password
        self.room_id = room_id
        self.access_token = None
        self.user_id = None
        self.sync_token = None
        self.running = False
        self.last_message_time = 0

    def login(self):
        """Login to Matrix server and get access token"""
        login_url = f"{self.homeserver}/_matrix/client/r0/login"
        payload = {
            "type": "m.login.password",
            "user": self.username,
            "password": self.password,
        }

        try:
            resp = requests.post(login_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            self.access_token = data["access_token"]
            self.user_id = data["user_id"]
            print(f"Logged in as {self.user_id}")
            return True
        except Exception as e:
            print(f"Login failed: {e}")
            # Try to register if login fails
            return self.register()

    def register(self):
        """Register a new user if login fails"""
        register_url = f"{self.homeserver}/_matrix/client/r0/register"
        payload = {
            "username": self.username,
            "password": self.password,
            "auth": {"type": "m.login.dummy"},
        }

        try:
            resp = requests.post(register_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            self.access_token = data["access_token"]
            self.user_id = data["user_id"]
            print(f"Registered and logged in as {self.user_id}")
            return True
        except Exception as e:
            print(f"Registration failed: {e}")
            return False

    def create_room(self, name="Cursor AI Chat"):
        """Create a new Matrix room"""
        if self.access_token is None:
            print("Need to login first")
            return False

        create_url = f"{self.homeserver}/_matrix/client/r0/createRoom"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "name": name,
            "preset": "private_chat",
            "visibility": "private",
            "initial_state": [],
        }

        try:
            resp = requests.post(create_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            self.room_id = data["room_id"]
            print(f"Created room: {self.room_id}")
            return True
        except Exception as e:
            print(f"Room creation failed: {e}")
            return False

    def send_message(self, message):
        """Send a message to the Matrix room"""
        if self.access_token is None or self.room_id is None:
            print("Need to login and have a room first")
            return False

        msg_url = f"{self.homeserver}/_matrix/client/r0/rooms/{self.room_id}/send/m.room.message"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {"msgtype": "m.text", "body": message}

        try:
            resp = requests.post(msg_url, headers=headers, json=payload)
            resp.raise_for_status()
            print(f"Message sent: {message[:50]}{'...' if len(message) > 50 else ''}")
            return True
        except Exception as e:
            print(f"Failed to send message: {e}")
            return False

    def sync(self):
        """Sync with Matrix server to get new messages"""
        sync_url = f"{self.homeserver}/_matrix/client/r0/sync"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {}

        if self.sync_token:
            params["since"] = self.sync_token
            params["timeout"] = 30000  # Long polling (30 seconds)

        try:
            resp = requests.get(sync_url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            self.sync_token = data["next_batch"]

            # Process new messages
            if self.room_id in data.get("rooms", {}).get("join", {}):
                room_data = data["rooms"]["join"][self.room_id]
                events = room_data.get("timeline", {}).get("events", [])

                for event in events:
                    if (
                        event.get("type") == "m.room.message"
                        and event.get("sender") != self.user_id
                    ):
                        # Skip messages we sent and messages older than our last check
                        ts = (
                            event.get("origin_server_ts", 0) / 1000
                        )  # Convert to seconds
                        if ts > self.last_message_time:
                            self.last_message_time = ts
                            sender = event.get("sender", "Unknown")
                            content = event.get("content", {})
                            body = content.get("body", "")

                            # Format timestamp
                            timestamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S")

                            # Print received message
                            print(f"\n[{timestamp}] {sender}: {body}")

            return True
        except Exception as e:
            print(f"Sync failed: {e}")
            return False

    def sync_loop(self):
        """Continuous sync loop in background thread"""
        self.running = True
        while self.running:
            if self.sync():
                # Continue immediately - the sync request itself has a timeout
                pass
            else:
                # If sync fails, wait a bit before retrying
                time.sleep(5)

    def start(self):
        """Start the Matrix relay"""
        if not self.login():
            print("Failed to login or register")
            return False

        if self.room_id is None:
            if not self.create_room():
                print("Failed to create room")
                return False

        # Start background sync thread
        sync_thread = threading.Thread(target=self.sync_loop)
        sync_thread.daemon = True
        sync_thread.start()

        print(f"Matrix relay started")
        print(f"Homeserver: {self.homeserver}")
        print(f"Room ID: {self.room_id}")
        print(f"User ID: {self.user_id}")
        print("\nType messages and press Enter to send. Ctrl+C to exit.")
        print("Messages from other users will appear automatically.\n")

        try:
            while True:
                message = input("> ")
                if message.strip():
                    self.send_message(message)
        except KeyboardInterrupt:
            print("\nExiting...")
            self.running = False
            return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Matrix Relay for AI Communication")
    parser.add_argument(
        "--homeserver", default=DEFAULT_HOMESERVER, help="Matrix homeserver URL"
    )
    parser.add_argument(
        "--room", default=DEFAULT_ROOM_ID, help="Room ID (will create if not provided)"
    )
    parser.add_argument("--user", default=DEFAULT_USER, help="Username")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Password")

    args = parser.parse_args()

    relay = MatrixRelay(
        homeserver=args.homeserver,
        username=args.user,
        password=args.password,
        room_id=args.room,
    )

    relay.start()
