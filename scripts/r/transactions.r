library(ggplot2)
library(reshape)
library(stringr)
library(igraph)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

if(file.exists("transactions_cumulative.csv")){
	df <- read.csv("transactions_cumulative.csv", sep=",")
    print(df)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_line(aes(time, transactions), colour='2')
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Total transactions completed\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="transactions.png", width=8, height=6, dpi=100)
}

# Draw the transaction graph
pdf(NULL)

library("igraph")

data = read.csv("transactions.log", sep=",")
data_matrix = data.matrix(data[,5:6])

g <- graph_from_edgelist(data_matrix, directed=F)

png(filename = "transaction_graph.png", width=1000, height=1000)

plot(g, layout=layout.fruchterman.reingold(g, niter=10000), vertex.size=8, edge.width=5)
title("Transactions", cex.main=3)

dev.off()
