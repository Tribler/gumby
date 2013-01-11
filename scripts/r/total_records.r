library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

if(file.exists("sum_total_records.txt")){
	df <- read.table("sum_total_records.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_step(data = df, alpha = 0.5)
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages received by peer\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="total_records.png", width=8, height=6, dpi=100)
}