library(ggplot2)
library(reshape)
library(stringr)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

if(file.exists("sum_statistics.txt")){
	df <- read.table("sum_statistics.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df <- subset(df, str_sub(variable, -1) != '_')
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_step(data = df)
	p <- p + opts(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Sum of statistic\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="statistics.png", width=8, height=6, dpi=100)
}