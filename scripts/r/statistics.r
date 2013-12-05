library(ggplot2)
library(reshape)
library(stringr)

if(file.exists("sum_statistics_reduced.txt")){
	df <- read.table("sum_statistics_reduced.txt", header = TRUE, check.names = FALSE)
	df <- df[,colSums(df) != 0]
	df <- melt(df, id="time")
	df <- subset(df, str_sub(variable, -1) != '_')
	p <- p + geom_point(data = df2)
	
	
	p <- ggplot(df2, aes(time, value, group=variable, colour=variable, shape=variable)) + theme_bw()
	p <- p + geom_step()
	p <- p + geom_point(data = df2)
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Sum of statistic\n")
	p

}