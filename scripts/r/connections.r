library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

i = 1
while(file.exists(paste("total_connections_", toString(i), "_reduced.txt", sep = ''))){
	df <- read.table(paste("total_connections_", toString(i), "_reduced.txt", sep = ''), header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_step(data = df, alpha = 0.5)
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Connections per peer\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file=paste("total_connections_", toString(i), ".png", sep = ''), width=8, height=6, dpi=100)
	i = i + 1
}