library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

if(file.exists("dropped_diff_reduced.txt")){
	df <- read.table("dropped_diff_reduced.txt", header = TRUE)
	df <- melt(df, id="time")
	df <- subset(df, df$value > 0)
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_point(aes(size=value), alpha = 5/10) + scale_size(range = c(1, 3))
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages dropped (Diff)\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="dropped_diff.png", width=8, height=6, dpi=100)
}

if(file.exists("dropped_reduced.txt")){
	df <- read.table("dropped_reduced.txt", header = TRUE)
	df <- melt(df, id="time")
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_step(alpha = 0.5)
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages dropped\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="dropped.png", width=8, height=6, dpi=100)
}