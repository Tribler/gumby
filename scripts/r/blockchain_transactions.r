library(ggplot2)
library(reshape)
library(stringr)
library(igraph)

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

if(file.exists("tx_cumulative.csv")){
	df <- read.csv("tx_cumulative.csv", sep=",")

	df <- melt(df, id=c("time"))
	df$time <- df$time / 1000
	print(df)

	p <- ggplot(df, aes(x=time, y=value, group=variable, colour=variable)) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_line()
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + xlab("Time into the experiment (sec)")
	p <- p + ylab("Number of transactions")
	p

	ggsave(file="transactions_cumulative.png", width=9, height=5, dpi=100)
}

# Draw the transaction graph
pdf(NULL)

dev.off()
