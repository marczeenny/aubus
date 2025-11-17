# AUBus Application Protocol (JSON-over-TCP)

This document summarizes the client↔server message types used by the AUBus application and a short example interaction for the assignment.

All messages are JSON objects with the following envelope:
{
  "type": "MESSAGE_TYPE",
  "payload": { ... }
}

Messages are sent over a TCP connection; each JSON message is encoded as UTF-8 and terminated with a newline.

Core message types (client -> server)
- REGISTER: Register a new user
  payload: { name, email, username, password, role, area?, schedule? }
  response: REGISTER_OK or REGISTER_FAIL

- LOGIN: Authenticate
  payload: { username, password }
  response: LOGIN_OK (payload=user info) or LOGIN_FAIL

- ANNOUNCE_PEER: Tell the server which local TCP port this client listens on for P2P chat
  payload: { port }
  response: ANNOUNCE_OK or ANNOUNCE_FAIL

- SET_ROLE, ADD_SCHEDULE, LIST_SCHEDULE, DELETE_SCHEDULE: schedule management

- BROADCAST_RIDE_REQUEST: Passenger asks for drivers in area/time
  payload: { passenger_id, direction, day, time, area }
  response: BROADCAST_OK (payload:{ride_id}) or NO_DRIVERS_FOUND

- DRIVER_RESPONSE: Driver accepts/denies a ride
  payload: { ride_id, status }
  response: DRIVER_RESPONSE_OK
  Notification sent to passenger: DRIVER_RESPONSE with payload { ride_id, status, driver_username?, driver_ip?, driver_port? }

- START_RIDE, COMPLETE_RIDE, CANCEL_RIDE: ride lifecycle operations

- SEND_MESSAGE: Server-relayed chat
  payload: { to: <username>, message: <text> }
  response: SEND_MESSAGE_OK or SEND_MESSAGE_FAIL

- ANNOUNCE and peer-related messages are used to enable a hybrid centralized + P2P design where the server coordinates and provides peer contact details so clients may open direct sockets to exchange messages.

Server -> client events (asynchronous notifications)
- RIDE_REQUEST: server notifies drivers about a new nearby passenger
  payload: { ride_id, passenger_id, passenger_name, direction, time }

- DRIVER_RESPONSE: passenger notified when a driver accepts or denies
  payload: { ride_id, status, driver_username?, driver_ip?, driver_port? }

- RIDE_STARTED / RIDE_COMPLETED / RIDE_CANCELLED: lifecycle events

- CHAT_MESSAGE: server-relayed chat messages (if P2P not used)
  payload: { from, from_id, to_id, message, sent_at }

Peer-to-peer message format (client -> client over TCP)
- Messages are JSON objects with a `type` and `payload`.
- Example for chat: { "type": "CHAT_PEER", "payload": { "from": "alice@example.com", "body": "Hi" } }

Sample interaction (passenger requests, driver accepts, P2P handshake):
1) Passenger registers and logs in using REGISTER / LOGIN.
2) Driver registers and logs in; both clients start a small peer TCP server and send ANNOUNCE_PEER with their listening port.
3) Passenger sends BROADCAST_RIDE_REQUEST with time/area.
4) Server runs matching and sends RIDE_REQUEST to matching drivers.
5) A driver responds with DRIVER_RESPONSE status = "ACCEPTED".
6) Server calls `accept_ride_request(...)` and notifies the passenger with DRIVER_RESPONSE (payload includes driver_username and driver's peer IP/port if announced).
7) Passenger receives DRIVER_RESPONSE and attempts to open a direct TCP socket to the provided driver IP/port and exchange CHAT_PEER messages directly.

Notes
- The server also supports server-relayed chat as a fallback (SEND_MESSAGE/CHAT_MESSAGE) to avoid NAT traversal complexities.
- This hybrid approach satisfies the requirement for hybrid client-server + peer-to-peer architecture: server coordinates and provides peer endpoints, while actual chat may go direct between clients when possible.
