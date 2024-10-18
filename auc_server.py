"""
Module Name: auc_server.py
Description: This script implements an auction server that manages the auction process.
             It listens for clients (buyers and sellers), handles auction requests,
             processes bids, and determines the winner based on first-price or 
             second-price auction types.

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
Run this script on a server to manage auctions. The first client connection will be 
treated as a seller, and subsequent connections will be buyers.

Example:
--------
$ python3 auc_server.py <port>

Where '<port>' is the TCP port where the server will listen.
"""

import socket
import threading
import sys

class AuctioneerServer:
    def __init__(self, host='localhost', port=65432):
        """
        Initialize the auctioneer server with the given host and port.
        The server binds to the port and listens for incoming connections.
        """
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', self.port))  # Bind to all interfaces
        self.server_socket.listen()
        print(f"Auctioneer is ready for hosting auctions!\n")

        # Server status and data structures
        self.status = 0  # 0: Waiting for Seller, 1: Waiting for Buyers
        self.seller = None
        self.buyer_threads = []
        self.buyers = []  # List of connected buyers
        self.buyer_bids = {}  # Dictionary to store buyer bids
        self.auction_details = {}  # Store auction-related details (e.g., type, price)
        self.bid_order = []  # Track the order in which bids are received for tie-breaking
        self.buyer_count = 0  # Counter for numbering buyers
        self.buyer_number_map = {}  # Map client sockets to buyer numbers
        self.lock = threading.Lock()  # Ensure thread-safe access to shared resources
        self.seller_request_received = False  # Track whether an auction request has been submitted

    def handle_client(self, client_socket, address):
        """
        Handle incoming client connections. If no seller has connected yet, assign the
        client as the seller. If a buyer tries to connect before the seller submits
        an auction request, the connection is rejected.
        """
        if self.seller is None:  # Expect the seller to connect first
            self.seller = client_socket
            self.status = 1  # Switch to waiting for buyers
            ip, port = address
            print(f"Seller is connected from {ip}:{port}")
            print(f">> New Seller Thread spawned")

            client_socket.send(b"submit an auction request")  # Prompt the seller for an auction request
            self.process_seller_request(client_socket)
        elif self.status == 1 and not self.seller_request_received:
            # Reject the buyer connection since no auction request has been submitted yet
            print("Buyer tried to connect before auction request submission.")
            client_socket.sendall(b"Server is busy. Try to connect again later.")
            client_socket.shutdown(socket.SHUT_WR)  # Ensure the message is sent before closing
            client_socket.close()
        elif self.status == 1 and self.seller_request_received:
            # Accept the buyer connection once the seller has submitted an auction request
            self.process_buyer(client_socket, address)

    def process_seller_request(self, client_socket):
        """
        Process the auction request from the seller. The seller submits auction details
        like auction type, minimum price, number of bids, and item name.
        """
        while True:
            try:
                message = client_socket.recv(1024).decode()
                auction_data = message.split()  # Expect space-separated values

                if len(auction_data) != 4:
                    client_socket.send(b"Invalid auction request!")  # Validate auction request
                    continue

                # Extract auction details from the request
                type_of_auction, lowest_price, number_of_bids, item_name = auction_data
                self.auction_details = {
                    "type": int(type_of_auction),
                    "lowest_price": int(lowest_price),
                    "num_bids": int(number_of_bids),
                    "item_name": item_name,
                }
                self.seller_request_received = True  # Mark that the auction request is received
                client_socket.send(f"Auction request received: {message}".encode())
                print(f"Auction request received. Now waiting for Buyers.\n")
                break
            except Exception as e:
                print(f"Error processing seller request: {e}")

    def process_buyer(self, client_socket, address):
        """
        Process the buyer connection and track their bids. Only allow buyers to connect
        after the seller has submitted an auction request and up to the specified number
        of buyers for the auction.
        """
        if len(self.buyers) < self.auction_details["num_bids"]:
            self.buyer_count += 1  # Increment the buyer count for each new buyer
            ip, port = address
            print(f"Buyer {self.buyer_count} is connected from {ip}:{port}")
            self.buyer_number_map[client_socket] = self.buyer_count  # Map socket to buyer number
            self.buyers.append(client_socket)  # Add the buyer to the list
            client_socket.send(b"waiting for other Buyers")

            # Once the required number of buyers are connected, start bidding
            if len(self.buyers) == self.auction_details["num_bids"]:
                print("Requested number of bidders arrived. Let's start bidding!\n")
                print(">> New Bidding Thread spawned")
                self.start_bidding()

        else:
            # Extra buyer connection if more than the required buyers attempt to join
            print(f"Extra Buyer tried to join. Informing that the auction is full.")
            client_socket.send(b"Server busy, auction in progress!")
            client_socket.close()

    def start_bidding(self):
        """
        Notify all buyers that the bidding process is starting and begin collecting bids.
        """
        for buyer in self.buyers:
            buyer.send(b"Bidding start! Please submit your bid.")

        # Start threads for handling bids from each buyer
        for buyer in self.buyers:
            threading.Thread(target=self.handle_bidding, args=(buyer, buyer.getpeername())).start()

    def handle_bidding(self, client_socket, address):
        """
        Handle incoming bids from buyers, validate the bid, and track the order in which
        bids are received for tie-breaking in case of equal bids.
        """
        buyer_number = self.buyer_number_map[client_socket]  # Get the buyer's number
        while True:
            try:
                bid = client_socket.recv(1024).decode()  # Receive the buyer's bid
                if bid.isdigit() and int(bid) > 0:  # Ensure the bid is a positive integer
                    with self.lock:
                        # Track the buyer's bid and the order in which it was received
                        self.buyer_bids[client_socket] = int(bid)
                        self.bid_order.append(client_socket)
                    print(f">> Buyer {buyer_number} bid ${bid}")
                    client_socket.send(b"Bid received. Please wait...\n")
                    break
                else:
                    client_socket.send(b"Invalid bid. Please submit a positive integer!")
            except Exception as e:
                print(f"Error handling bid from Buyer {buyer_number}: {e}")
                break

        # If all expected bids have been received, process the auction results
        if len(self.buyer_bids) == self.auction_details["num_bids"]:
            self.process_auction_results()

    def process_auction_results(self):
        """
        Process the results of the auction by determining whether the highest bid meets
        the minimum price requirement. If no bids are sufficient, the item is not sold.
        """
        highest_bid = max(self.buyer_bids.values())
        lowest_price = self.auction_details["lowest_price"]

        if highest_bid < lowest_price:
            # If all bids are below the lowest price, the item is not sold
            print(f">> All bids are below the minimum price of ${lowest_price}. The item is not sold.")
            self.notify_seller(f"Item not sold. All bids were below the minimum price of ${lowest_price}.")
            self.notify_all_buyers("Auction finished!")
            self.notify_all_buyers("\nUnfortunately you did not win in the last round.")
            self.notify_all_buyers("\nDisconnecting from the Auctioneer server. Auction is over!")
        else:
            # Proceed with selling the item to the highest bidder
            self.process_winner(highest_bid)

        self.reset_auction()

    def process_winner(self, highest_bid):
        """
        Identify the winning buyer and notify them. If the auction type is second-price,
        the second-highest bid is used as the payment amount.
        """
        winning_buyer = None
        for buyer in self.bid_order:  # Identify the first buyer who submitted the highest bid
            if self.buyer_bids[buyer] == highest_bid:
                winning_buyer = buyer
                break

        lowest_price = self.auction_details["lowest_price"]
        item_name = self.auction_details["item_name"]

        if highest_bid >= lowest_price:
            if self.auction_details["type"] == 1:  # First-price auction
                winning_price = highest_bid
                print(f">> Item sold! The highest bid is ${highest_bid}. The actual payment is ${winning_price}")
                self.notify_winner(winning_buyer, winning_price)
            else:  # Second-price auction
                second_highest_bid = max(
                    [b for b in self.buyer_bids.values() if b != highest_bid],
                    default=lowest_price,
                )
                winning_price = second_highest_bid
                print(f">> Item sold! The highest bid is ${highest_bid}. The actual payment is ${winning_price}")
                self.notify_winner(winning_buyer, winning_price)

    def notify_winner(self, winning_buyer, payment):
        """
        Notify the winning buyer of their success and the payment amount, and inform the
        losing buyers that they did not win.
        """
        item_name = self.auction_details["item_name"]

        # Notify the winning buyer with the item name and payment
        winning_buyer.sendall(f"Auction finished!\nYou won the item '{item_name}'! Your payment due is ${payment}".encode())
        winning_buyer.send(f"\nDisconnecting from the Auctioneer server. Auction is over!".encode())

        # Notify the losing buyers
        for buyer, bid in self.buyer_bids.items():
            if buyer != winning_buyer:
                buyer.send(f"Auction finished!".encode())
                buyer.send(b"\nUnfortunately you did not win in the last round.")
                buyer.send(f"\nDisconnecting from the Auctioneer server. Auction is over!".encode())

        # Notify the seller of the successful sale
        self.notify_seller(f"Item '{item_name}' sold for ${payment}.")

    def notify_seller(self, message):
        """Notify the seller with the final auction result and close the connection."""
        self.seller.send(message.encode())
        self.seller.close()

    def notify_all_buyers(self, message):
        """Notify all buyers with the given message."""
        for buyer in self.buyer_bids:
            try:
                buyer.send(message.encode())
            except OSError:
                print(f"Error: Unable to send message to a buyer (bad file descriptor).")
                continue  # Continue notifying the rest of the buyers

    def reset_auction(self):
        """Reset the auction state for a new round after the current auction completes."""
        self.status = 0
        self.seller = None
        self.buyer_bids.clear()
        self.buyers.clear()  # Clear buyer list
        self.bid_order.clear()  # Reset the order of bids
        self.buyer_number_map.clear()  # Clear the buyer number mapping
        self.auction_details.clear()
        self.buyer_threads.clear()
        self.seller_request_received = False  # Reset for the next auction

    def start(self):
        """Start the auctioneer server and listen for incoming client connections."""
        while True:
            client_socket, address = self.server_socket.accept()
            threading.Thread(
                target=self.handle_client, args=(client_socket, address)
            ).start()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 auctioneer_server.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    auctioneer_server = AuctioneerServer(port=port)
    auctioneer_server.start()
