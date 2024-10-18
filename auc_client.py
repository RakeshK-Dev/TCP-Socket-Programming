"""
Module Name: auc_client.py
Description: This script implements a client that can either act as a seller or a buyer.
             The seller submits an auction request, and buyers submit bids. 
             The server manages the auction process and determines the winner.

Developer Information:
-----------------------
- Author: Rakesh Kannan, Sharmila Reddy Anugula 
- Email: rkannan3@ncsu.edu, sanugul@ncsu.edu
- GitHub: https://github.com/RakeshK-Dev
- Created Date: 2024-10-01
- Last Modified: 2024-10-17
- Version: 1.0.0

Usage:
------
Run this script to connect to the auction server as either a seller or buyer.
The server must be running for this client to connect.

Example:
--------
$ python3 auc_client.py <host> <port>

Where '<host>' is the server's IP address, and '<port>' is the port number the server is listening on.
"""

import socket
import sys

class AuctionClient:
    def __init__(self, host, port):
        """Initialize the client with the server's host and port details."""
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a TCP socket
        self.item_name = None  # Track the item name for the seller
        self.payment = None  # Track the payment for the item

    def connect_to_server(self):
        """Attempt to connect to the auctioneer server."""
        try:
            self.client_socket.connect((self.host, self.port))  # Connect to the server
            print(f"Connected to the Auctioneer server.\n")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
        return True

    def send_message(self, message):
        """Send a message to the server."""
        try:
            self.client_socket.sendall(message.encode())  # Ensure full message is sent
        except (BrokenPipeError, ConnectionResetError):
            print("Server connection lost.")
            self.client_socket.close()  # Close the socket on error

    def receive_message(self):
        """Receive a message from the server."""
        try:
            return self.client_socket.recv(1024).decode()  # Receive data from the server
        except (ConnectionResetError, socket.error):
            return None  # Return None if there is a connection error

    def run(self):
        """Main method to start the client, decide role (seller/buyer), and handle the auction process."""
        if not self.connect_to_server():  # Connect to the server
            return

        response = self.receive_message()  # Wait for a message from the server

        if response is None:
            print("Server is busy. Try to connect again later.")
            self.client_socket.close()  # Close the connection
            return

        # If the server responds with "Server busy"
        if "Server busy" in response:
            print("Server is busy. Try to connect again later.")
            self.client_socket.close()  # Close the connection
            return

        # Determine whether the client is the seller or a buyer
        if "submit an auction request" in response:
            print("Your role is: [Seller]")
            self.seller_mode()  # Start seller mode
        elif "waiting for other Buyers" in response:
            print("Your role is: [Buyer]")
            print("The Auctioneer is still waiting for other Buyers to connect...\n")
            self.wait_for_bidding()  # Wait for the bidding to start
        else:
            print("Server is busy. Try to connect again later.")
            self.client_socket.close()  # Close the connection
            return

    def seller_mode(self):
        """Handle the auction request submission by the seller."""
        while True:
            print("Please submit auction request:")
            auction_details = input()  # Get auction details from the seller

            try:
                # Split the auction details into type, lowest price, number of bids, and item name
                auction_type, lowest_price, num_bids, item_name = auction_details.split(maxsplit=3)
                message = f"{auction_type.strip()} {lowest_price.strip()} {num_bids.strip()} {item_name.strip()}"
                self.item_name = item_name  # Store the item name for later use
                self.send_message(message)  # Send the auction request to the server

                response = self.receive_message()
                if response is None:
                    print("Server is busy. Try to connect again later.")
                    break

                print(f"Server: Auction start.\n")

                # Check if the auction request is received by the server
                if "Auction request received" in response:
                    response = self.receive_message()  # Receive further responses

                    if response is None:
                        print("Server is busy. Try to connect again later.")
                        break

                    # Check if the item was sold or not
                    if "Item not sold" in response:
                        print(f"Auction finished!")
                        print("Unfortunately, your item was not sold as all bids were below the minimum price.")
                    elif "sold" in response:
                        # Extract the payment amount from the server response
                        sold_message = response.split(" ")
                        self.payment = sold_message[-1].replace("$", "")
                        print("Auction finished!")
                        print(f"Success! Your item {self.item_name} has been sold for ${self.payment}")
                    else:
                        print(f"Auction finished: {response}")
                    
                    print(f"Disconnecting from the Auctioneer server. Auction is over!")
                    break
            except ValueError:
                print("Server: Invalid auction request!")

    def wait_for_bidding(self):
        """Wait for the bidding process to start and handle it."""
        response = self.receive_message()
        if "Bidding start!" in response:
            print("The bidding has started!")
            self.buyer_mode()

    def buyer_mode(self):
        """Handle the bidding process for the buyer."""
        while True:
            print("Please submit your bid:")
            bid = input()  # Get the bid from the buyer
            self.send_message(bid)  # Send the bid to the server
            response = self.receive_message()  # Wait for the server response

            if response is None:
                print("Server is busy. Try to connect again later.")
                break

            print(f"Server: {response}")

            if "Bid received" in response:
                response = self.receive_message()  # Wait for the auction result
                if response is None:
                    print("Server is busy. Try to connect again later.")
                    break
                print(f"Server: {response}")
                break

if __name__ == "__main__":
    # Ensure correct command-line arguments for host and port
    if len(sys.argv) != 3:
        print("Usage: python3 auction_client.py <host> <port>")
        sys.exit(1)

    # Get the server host and port from command-line arguments
    host = sys.argv[1]
    port = int(sys.argv[2])

    # Create a new client and run it
    client = AuctionClient(host, port)
    client.run()
