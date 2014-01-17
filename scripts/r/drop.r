library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

if(file.exists("dropped_diff_reduced.txt")){
	df <- read.table("dropped_diff_reduced.txt", header = TRUE)
	df <- melt(df, id="time")
	df <- subset(df, df$value > 0)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df2)
	p <- p + geom_point(alpha = 0.8, aes(time, value, size=value, group=variable, colour=variable)) + scale_size(range = c(1, 3))
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages dropped (Diff)\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="dropped_diff.png", width=8, height=6, dpi=100)
}

if(file.exists("dropped_reduced.txt")){
	df <- read.table("dropped_reduced.txt", header = TRUE)
	num_columns <- ncol(df) - 1
	df <- mean_max_min(num_columns, df)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df2)
	if (num_columns <= 1000){
		p <- p + geom_step(alpha = 0.8, aes(time, value, group=variable, colour=variable))
	} else {
		p <- p + geom_step(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages dropped\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="dropped.png", width=8, height=6, dpi=100)
}