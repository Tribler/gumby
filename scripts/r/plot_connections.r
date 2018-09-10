library(ggplot2)
library(reshape)
library(stringr)
library(igraph)

# Draw the transaction graph
pdf(NULL)

library("igraph")

data = read.csv("peer_connections.log", sep=",")
data_matrix = data.matrix(data[,1:2])

g <- graph_from_edgelist(data_matrix, directed=T)

png(filename = "peer_connections.png", width=1000, height=1000)

plot(g, layout=layout.fruchterman.reingold(g, niter=10000), vertex.size=6, edge.width=3)
title("Peer connections", cex.main=3)

dev.off()
