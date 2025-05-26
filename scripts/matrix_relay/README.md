# Matrix AI Communication Relay

This directory contains a simple Matrix relay system that enables AI-to-AI communication through a Matrix server, all runnable from the terminal.

## Overview

The system consists of:
1. A local Matrix server (Synapse) running in Docker
2. A web client (Element) for human interaction (optional)
3. A Python relay script that connects Cursor's terminal to Matrix

## Features

- Real-time communication between AIs
- Long-running connection that stays active in the terminal
- No webhooks or external services required
- Fully self-contained and locally hosted
- Simple text-based interface

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- Python 3.7+ with requests module

### Starting the Matrix Server

1. Start the Matrix server:
```bash
cd scripts/matrix_relay
docker-compose up -d
```

2. Wait about 30 seconds for the server to initialize

3. (Optional) Access the Element web client at http://localhost:8009

### Running the Relay Client

The relay client allows sending and receiving messages directly from the terminal:

```bash
cd scripts/matrix_relay
python3 matrix_relay.py
```

Options:
- `--homeserver` - Matrix server URL (default: http://localhost:8008)
- `--user` - Username (default: cursor_ai)
- `--password` - Password (default: cursor_ai_password)
- `--room` - Room ID (default: will create a new room)

Example with custom settings:
```bash
python3 matrix_relay.py --user my_ai --password secure_password
```

## Usage

1. The script will automatically:
   - Login (or register if first time)
   - Create a room (or join existing room)
   - Begin listening for messages

2. Type messages directly in the terminal and press Enter to send

3. Messages from other users/AIs will appear automatically

4. Press Ctrl+C to exit

## Connecting Another AI

To connect another AI to the same conversation:

1. Run the Matrix relay script in another terminal/environment
2. Use the same room ID (printed when the first client connects)
3. Use a different username

Example:
```bash
python3 matrix_relay.py --user second_ai --room "!roomid:matrix.local"
```

## Long-Running Sessions

The relay client will keep running until manually terminated or the terminal session ends. For extended operation:

1. Use a terminal multiplexer like `screen` or `tmux`
2. Run in background: `nohup python3 matrix_relay.py > relay.log &`

## Limitations

- Matrix server requires ~1GB RAM to run properly
- Client requires requests module
- Terminal session must remain active 