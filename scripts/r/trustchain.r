library(ggplot2)
library(reshape)
library(stringr)
library(igraph)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

if(file.exists("leader_blocks_time_1.csv")) {
    lead_csv <- read.csv("leader_blocks_time_1.csv", sep=',', header=T)
    val <- qplot(lead_csv$time, geom="histogram", binwidth = 1.0,
      xlab="\nTime into experiment (Seconds)",
      ylab="Total TrustChain blocks count\n", main="Time of blocks arrived at leader node",
      fill=I("blue"),
      col=I("red"),
      alpha=I(.2))
    val
    ggsave(file="leader_blocks_hist.png", width=8, height=6, dpi=100)
}

if(file.exists("trustchain.csv")) {
	df <- read.csv("trustchain.csv", sep=";", header=T)
    df$freq <- 1
    df$time_since_start <- df$time_since_start / 1000
    df <- df[order(df$time_since_start),]

	p <- ggplot(df, aes(x=time_since_start, y=cumsum(freq))) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_line()
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Total TrustChain blocks created\n")
	p <- p + xlim(minX, maxX)
	p

	ggsave(file="trustchain_blocks_created.png", width=8, height=6, dpi=100)
}

if(file.exists("trustchain_interactions.csv")) {
    # Draw the transaction graph
    pdf(NULL)

    data = read.csv("trustchain_interactions.csv", sep=",")
    data_matrix = data.matrix(data[,1:2])

    g <- graph_from_edgelist(data_matrix, directed=F)

    png(filename = "trustchain_interactions.png", width=1000, height=1000)

    plot(g, layout=layout.fruchterman.reingold(g, niter=10000), vertex.size=6, edge.width=3)
    title("TrustChain Interactions", cex.main=3)

    dev.off()
}
