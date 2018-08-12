library(ggplot2)
library(reshape)
library(stringr)
library(igraph)

# Draw the transaction graph
pdf(NULL)

library("igraph")

data = read.csv("trustchain_interactions.csv", sep=",")
data_matrix = data.matrix(data[,1:2])

g <- graph_from_edgelist(data_matrix, directed=F)

png(filename = "trustchain_interactions.png", width=1000, height=1000)

plot(g, layout=layout.fruchterman.reingold(g, niter=10000), vertex.size=6, edge.width=3)
title("TrustChain Interactions", cex.main=3)

dev.off()
