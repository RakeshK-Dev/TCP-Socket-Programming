# TCP-Socket-Programming
A multi-threaded auction system where users can connect as sellers or buyers via TCP. Sellers create auctions with item details, and buyers place bids. The server manages concurrent connections, processes bids, and announces winners based on auction type (first-price or second-price). Implements socket programming for real-time auction handling.

How to run the code :

Module Name : auc_server.py

Description : This script implements an auction server that manages the auction process. It listens for clients (buyers and sellers), handles auction requests, processes bids, and determines the winner based on first-price or second-price auction types.

Usage : Run this script on a server to manage auctions. The first client connection will be 
treated as a seller, and subsequent connections will be buyers.

Example :
$ python3 auc_server.py <port<port>>

Where '<port<port>>' is the TCP port where the server will listen.

Module Name : auc_client.py

Description : This script implements a client that can either act as a seller or a buyer. The seller submits an auction request, and buyers submit bids. The server manages the auction process and determines the winner.

Usage : Run this script to connect to the auction server as either a seller or buyer. The server must be running for this client to connect.

Example :
$ python3 auc_client.py <host<host>> <port<port>>

Where '<host<host>>' is the server's IP address, and '<port<port>>' is the port number the server is listening on.
