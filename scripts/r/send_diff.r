library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

if(file.exists("send_diff_reduced.txt")){
	df <- read.table("send_diff_reduced.txt", header = TRUE, check.names = FALSE)
	num_columns <- ncol(df) - 1
	df <- mean_max_min(num_columns, df)
	df$value = df$value/1024.0
	
	if (num_columns <= 1000){
		df <- subset(df, df$value > 0)
	}
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df2)
	if (num_columns <= 1000){
		p <- p + geom_point(data = df, aes(time, value, group=variable, colour=variable, size=value), alpha=0.8)  + scale_size(range = c(1, 3))
	} else {
		p <- p + geom_line(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage for peer (KiBytes/s upload)\n")
	p <- p + xlim(minX, maxX)
	p
	ggsave(file="send_diff.png", width=8, height=6, dpi=100)
}

if(file.exists("received_diff_reduced.txt")){
	df <- read.table("received_diff_reduced.txt", header = TRUE, check.names = FALSE)
	num_columns <- ncol(df) - 1
	df <- mean_max_min(num_columns, df)
	df$value = df$value/1024.0
	
	if (num_columns <= 1000){
		df <- subset(df, df$value > 0)
	}
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df2)
	if (num_columns <= 1000){
		p <- p + geom_point(data = df, aes(time, value, group=variable, colour=variable, size=value), alpha=0.8)  + scale_size(range = c(1, 3))
	} else {
		p <- p + geom_line(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage for peer (KiBytes/s download)\n")
	p <- p + xlim(minX, maxX)
	p
	ggsave(file="received_diff.png", width=8, height=6, dpi=100)
}