library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

if(file.exists("sum_total_records_reduced.txt")){
	df <- read.table("sum_total_records_reduced.txt", header = TRUE, check.names = FALSE, na.strings = "?")
	df <- melt(df, id="time")
	df <- na.omit(df)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_step(alpha = 0.8, aes(time, value, group=variable, colour=variable))
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages received by peer\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="total_records.png", width=8, height=6, dpi=100)
}