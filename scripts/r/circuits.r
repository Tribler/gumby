library(ggplot2)
library(reshape)
library(stringr)
library(igraph)

# Draw the transaction graph
pdf(NULL)

library("igraph")

data = read.csv("circuits_graph.csv", sep=",")
print(data)

g <- make_empty_graph(n=0)

addVertIfNotPresent <- function(g, ...){
  names2add <- setdiff(list(...),V(g)$name)
  v2add <- do.call(vertices,names2add)
  g <- g + v2add
}

for(row in 1:nrow(data)) {
    from <- toString(data[row, "from"])
    to <- toString(data[row, "to"])
    circuit_num <- data[row, "circuit_num"]
    circuit_type <- data[row, "type"]
    bytes_transferred = toString(data[row, "bytes_transferred"])

    lty <- "solid"
    if (circuit_type == "RP") { lty <- "dotted" }
    else if (circuit_type == "IP") { lty <- "dotdash" }

    g <- addVertIfNotPresent(g, from)
    g <- addVertIfNotPresent(g, to)
    g <- add_edges(g, c(from, to), color=circuit_num, label=bytes_transferred, lty=lty)
}

g <- as.undirected(g, mode="each")

png(filename = "circuits.png", width=1000, height=1000)

plot(g, layout=layout.fruchterman.reingold(g, niter=10000), vertex.size=10, edge.width=5)
title("Circuits", cex.main=3)

dev.off()
