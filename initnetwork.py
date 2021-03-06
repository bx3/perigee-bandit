#!/usr/bin/env python
import networkx as nx
from math import radians, cos, sin, asin, sqrt
import numpy as np
import matplotlib.pyplot as plt
import random
import data
import sys
import math
import readfiles
from collections import defaultdict
import config
from config import *


def construct_graph(nodes, ld):
    num_nodes = len(nodes)
    G = nx.Graph()
    for i, node in nodes.items():
        for u in node.outs:
            delay = ld[i][u] + node.node_delay/2 + nodes[u].node_delay/2
            assert(i != u)
            G.add_edge(i, u, weight=delay)
    return G

def construct_graph_revise(nodes, ld):
    pass

def reduce_link_latency(num_node, num_low_latency, ld):
    all_nodes = [i for i in range(num_node)]
    random.shuffle(all_nodes)
    all_nodes = list(all_nodes)
    low_lats = all_nodes[:num_low_latency]

    for i in low_lats:
        for j in low_lats:
            if i != j:
                ld[i][j] *= config.reduce_link_ratio 

def generate_random_outs_conns(out_lim, in_lim, num_node):
    outs_conns = defaultdict(list) 
    order = [i for i in range(num_node)]
    in_counts = {i:0 for i in range(num_node)}

    for _ in range(out_lim):
        random.shuffle(order)
        for i in order:
            w = np.random.randint(num_node)
            while ( w in outs_conns[i] or
                    w == i or
                    in_counts[w] >= in_lim or
                    i in outs_conns[w]
                    ):
                w = np.random.randint(num_node)
            outs_conns[i].append(w)

    return outs_conns




# Generate the initial graph with all the lawful users
def GenerateInitialGraph():
    G = nx.Graph()
    data_file = open(config.data_file, 'r', errors='replace')
    line = data_file.readline()
    lines = line.split('],')
    k=0
    for i in range(9559):
        a = lines[i].split(',')
        if(data.con[a[7]]!="Null"):
            G.add_node(k,country=a[7], cluster=data.con[a[7]])
            k=k+1
    data_file.close()
    return(G)

# Generate nodes' processing delay
def GenerateInitialDelay(num_node):
    delay=[0 for i in range(num_node)]
    for i in range(num_node):
        buff= np.random.normal(config.node_delay_mean, config.node_delay_std)
        delay[i]=round(buff,6)
    return(delay)

# Generate the random neighbor connection
def GenerateOutNeighbor(len_of_neigh,IncomingLimit, num_node):
    OutNeighbor= np.zeros([num_node,len_of_neigh], dtype=np.int32)
    IncomingNeighbor=np.zeros(num_node, dtype=np.int32)
    for i in range(num_node):
        for j in range(len_of_neigh):
            OutNeighbor[i][j]=np.random.randint(num_node)
            out_peer = int(OutNeighbor[i][j])
            while( (out_peer in OutNeighbor[i][:j]) or 
                   (out_peer==i) or 
                   IncomingNeighbor[out_peer]>=IncomingLimit[out_peer] 
                  or (out_peer < i and i in OutNeighbor[out_peer] )):
                OutNeighbor[i][j]=np.random.randint(num_node)
                out_peer = int(OutNeighbor[i][j])
            IncomingNeighbor[out_peer]=IncomingNeighbor[out_peer]+1
    return(OutNeighbor,IncomingNeighbor)
    
    
# NeighborSets, contains connectionconuts and  all neighbor ids (including the incomings)
def GenerateInitialConnection(OutNeighbor,len_of_neigh, num_node):
    NeighborSets = np.zeros([num_node, config.in_lim+1+len_of_neigh ]) #225+len_of_neigh]) #225+len_of_neigh 1001
    for i in range(num_node):
        NeighborSets[i][0]=8
        for j in range(len_of_neigh):
            NeighborSets[i][1+j]=int(OutNeighbor[i][j])

    for i in range(num_node):
        for j in range(len_of_neigh):
            peer = int(OutNeighbor[i][j])
            peer_conn_count = int(NeighborSets[peer][0])
            # print("node",i, "peer",  peer, "peer_conn_count", peer_conn_count)
            # TODO is it not a bug?
            if i not in NeighborSets[peer][1:peer_conn_count+1]:
                NeighborSets[peer][peer_conn_count+1]=i
                NeighborSets[peer][0] += 1
    return(NeighborSets)

# if the block size is large enough, get linkdelays by the bandwidth
def DelayByBandwidth(NeighborSets,bandwidth, num_node):
    weight_table=np.zeros([num_node,num_node])
    for i in range(num_node):
        for j in range(len_of_neigh):
            if i != j :
                weight_table[i][int(OutNeighbor[i][j])] = 8 / min(bandwidth[i]/int(NeighborSets[i][0]) , bandwidth[int(OutNeighbor[i][j])]/int(NeighborSets[int(OutNeighbor[i][j])][0]))
    return(weight_table)
    
# Build graph edges
def BuildNeighborConnection(G,OutNeighbor,LinkDelay,delay,len_of_neigh, num_node):
    for i in range(num_node):
        for j in range(len_of_neigh):
            # plus half of both two sides' processing delay so that the node's processing delay can also be considered during shortest path searching
            G.add_edge(i,OutNeighbor[i][j],weight=LinkDelay[i][int(OutNeighbor[i][j])]+delay[i]/2+delay[int(OutNeighbor[i][j])]/2)
    return(G)

def InitBandWidth(num_node):
    bandwidth=np.zeros(num_node)
    for i in range(num_node):
        if (random.random()<0.33):
            bandwidth[i]=50
        else:
            bandwidth[i]=12.5
    return(bandwidth)

def InitIncomLimit(num_node):
    IncomingLimit=np.zeros(num_node)
    for i in range(num_node):
        #IncomingLimit[i]=min(int(bandwidth[i]*1.5),200)
        IncomingLimit[i]=config.in_lim
    return(IncomingLimit)


def GenerateInitialNetwork( NetworkType, num_node, subcommand, out_lim):
    bandwidth=InitBandWidth(num_node)
    IncomingLimit   =   InitIncomLimit(num_node)
    # G               =   GenerateInitialGraph()
    NodeDelay       =   GenerateInitialDelay(num_node)
    if subcommand == 'run-mf' or subcommand == 'run-2hop':
        [OutNeighbor,IncomingNeighbor]     =   GenerateOutNeighbor(out_lim,IncomingLimit, num_node)
    else:
        OutNeighbor = None
        IncomingNeighbor = None

    NeighborSets = None

    [LinkDelay,NodeHash,NodeDelay] = readfiles.Read(NodeDelay, NetworkType, num_node)

    if config.is_load_conn:
        print("\033[91m" + 'Use. Preset conn'+ "\033[0m")
        out_conns = {}
        with open(config.conn_path) as f:
            for line in f:
                tokens = line.strip().split(' ')
                out_conns[int(tokens[0])] = [int(i) for i in tokens[1:]]
        OutNeighbor = out_conns
    else:
        print("\033[93m" + 'Not use. Preset conn'+ "\033[0m")

    return(NodeDelay,NodeHash,LinkDelay,NeighborSets,IncomingLimit,OutNeighbor,IncomingNeighbor,bandwidth)
 
# Update graph by the latest neighbor connections
def UpdateNetwork(G,OutNeighbor,LinkDelay,NodeDelay,len_of_neigh,NeighborSets,bandwidth):
    NeighborSets=   GenerateInitialConnection(OutNeighbor,len_of_neigh)
    #LinkDelay=   initnetwork.DelayByBandwidth(NeighborSets,bandwidth)
    G           =   BuildNeighborConnection(G,OutNeighbor,LinkDelay,NodeDelay,len_of_neigh, num_node)
    return(NeighborSets,LinkDelay,G)

