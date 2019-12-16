#!/usr/bin/env python2
# Copyright (c) 2014 The Bitcoin Core developers
# Copyright (c) 2018 The Zencash developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
from test_framework.test_framework import BitcoinTestFramework
from test_framework.authproxy import JSONRPCException
from test_framework.util import assert_equal, initialize_chain_clean, \
    start_nodes, start_node, connect_nodes, stop_node, stop_nodes, \
    sync_blocks, sync_mempools, connect_nodes_bi, wait_bitcoinds, p2p_port, check_json_precision
import traceback
import os,sys
import shutil
from random import randint
from decimal import Decimal
import logging

import time
class headers(BitcoinTestFramework):

    alert_filename = None

    def setup_chain(self, split=False):
        print("Initializing test directory "+self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 3)
        self.alert_filename = os.path.join(self.options.tmpdir, "alert.txt")
        with open(self.alert_filename, 'w'):
            pass  # Just open then close to create zero-length file

    def setup_network(self, split=False):
        self.nodes = []

        self.nodes = start_nodes(3, self.options.tmpdir, extra_args=
            [['-debug=py', '-debug=sc', '-debug=mempool', '-debug=net', '-debug=cert', '-logtimemicros=1']] * 3 )

        connect_nodes_bi(self.nodes, 0, 1)
        connect_nodes_bi(self.nodes, 1, 2)
        sync_blocks(self.nodes[1:3])
        sync_mempools(self.nodes[1:3])
        self.is_network_split = split
        self.sync_all()

    def disconnect_nodes(self, from_connection, node_num):
        ip_port = "127.0.0.1:"+str(p2p_port(node_num))
        from_connection.disconnectnode(ip_port)
        # poll until version handshake complete to avoid race conditions
        # with transaction relaying
        while any(peer['version'] == 0 for peer in from_connection.getpeerinfo()):
            time.sleep(0.1)

    def dump_ordered_tips(self, tip_list):
        sorted_x = sorted(tip_list, key=lambda k: k['status'])
        c = 0
        for y in sorted_x:
            if (c == 0):
                print y 
            else:
                print " ",y 
            c = 1

    def mark_logs(self, msg):
        print msg
        self.nodes[0].dbg_log(msg)
        self.nodes[1].dbg_log(msg)

    def run_test(self):

        # side chain id
        scid = "1111111111111111111111111111111111111111111111111111111111111111"

        #forward transfer amount
        creation_amount = Decimal("0.5")
        fwt_amount = Decimal("2.5")
        bwt_amount = Decimal("100.0")

        blocks = []
        self.bl_count = 0

        blocks.append(self.nodes[0].getblockhash(0))

        # node 1 earns some coins, they would be available after 100 blocks 
        self.mark_logs("Node 1 generates 1 block")

        blocks.extend(self.nodes[1].generate(1))
        self.sync_all()

        self.mark_logs("Node 0 generates 220 block")

        blocks.extend(self.nodes[0].generate(220))
        self.sync_all()

        print "\nNode1 balance: ", self.nodes[1].getbalance("", 0)

        self.mark_logs("\nNode 1 creates the SC spending "+str(creation_amount)+" coins ...")
#        raw_input("press enter to go on..")
        amounts = []
        amounts.append( {"address":"dada", "amount": creation_amount})
        creating_tx = self.nodes[1].sc_create(scid, 123, amounts);
        print "tx = " + creating_tx
        self.sync_all()

        self.mark_logs("\nNode0 generating 1 block")
        blocks.extend(self.nodes[0].generate(1))
        ownerBlock = blocks[-1]
        self.sync_all()

        taddr = self.nodes[1].getnewaddress();
        self.mark_logs("\nNode 0 performs a bwd transfer of "+str(bwt_amount)+" coins to taddr["+str(taddr)+"]...")
#        raw_input("press enter to go on..")
        amounts = []
        amounts.append( {"address":taddr, "amount": bwt_amount})
        cert = self.nodes[0].sc_bwdtr(scid, amounts);
        print "cert = " + cert
        #self.sync_all()
        time.sleep(1)

        print "\nChecking mempools..."
        print "Node 0: ", self.nodes[0].getrawmempool()
        print "Node 1: ", self.nodes[1].getrawmempool()

        print "\nNode1 balance: ", self.nodes[1].getbalance("", 0)

        print("\nNode0 generating 1 honest block")
        blocks.extend(self.nodes[0].generate(1))
        self.sync_all()
        #time.sleep(1)

        print "Node0 balance: ", self.nodes[0].getbalance("", 0)
        print "Node1 balance: ", self.nodes[1].getbalance("", 0)
        print "Node2 balance: ", self.nodes[2].getbalance("", 0)

        self.mark_logs("\nNode 1 sends "+str(bwt_amount/2)+" coins to node2...")
        tx = self.nodes[1].sendtoaddress(self.nodes[2].getnewaddress(), bwt_amount/2)

        # check that input is formed using the certificate
        vin = self.nodes[1].getrawtransaction(tx, 1)['vin']
        assert_equal(vin[0]['txid'], cert)

        print("\nNode0 generating 1 honest block")
        blocks.extend(self.nodes[0].generate(1))
        self.sync_all()
        #time.sleep(1)

        print "Node0 balance: ", self.nodes[0].getbalance("", 0)
        print "Node1 balance: ", self.nodes[1].getbalance("", 0)
        print "Node2 balance: ", self.nodes[2].getbalance("", 0)
        print



if __name__ == '__main__':
    headers().main()