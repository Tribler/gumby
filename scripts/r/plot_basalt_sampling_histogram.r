library(ggplot2)
library(stringr)

if(file.exists("peer_samples.csv")){
	df <- read.csv("peer_samples.csv", sep=",")

	p <- ggplot(df, aes(x=peer_id)) + theme_bw()
	p <- p + geom_histogram(color="black", fill="gray", binwidth=1)
	p <- p + xlab("Peer ID")
	p <- p + ylab("Times sampled")
	p

	ggsave(file="basalt_peer_sample_histogram.png", width=9, height=5, dpi=100)
}

# Draw the transaction graph
pdf(NULL)

dev.off()
