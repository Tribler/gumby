library(ggplot2)
library(reshape)
library(stringr)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

if(file.exists("sum_statistics_reduced.txt")){
	df <- read.table("sum_statistics_reduced.txt", header = TRUE, check.names = FALSE, na.strings = "?")
	df <- df[,colSums(df) != 0]
	df <- melt(df, id="time")
	df <- na.omit(df)
	df <- subset(df, str_sub(variable, -1) != '_')
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_step(alpha = 0.8, aes(time, value, group=variable, colour=variable, shape=variable))
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Sum of statistic\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="statistics.png", width=8, height=6, dpi=100)
}