library(ggplot2)
library(reshape)

args <- commandArgs(TRUE)
minX <- as.integer(args[1])
maxX <- as.integer(args[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df3 <- load_annotations()

if(file.exists("rchars_reduced.txt")){
	df <- read.table("rchars_reduced.txt", header = TRUE, check.names = FALSE)
	num_columns <- ncol(df) - 1
	df <- mean_max_min(num_columns, df)
	df$type <- 'Process'
	
	df2 <- read.table("rchars_node_reduced.txt", header = TRUE, check.names = FALSE)
	df2 <- mean_max_min(num_columns, df2)
	df2$type <- 'Node'
	
	df <- rbind(df, df2)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df3)
	if (num_columns <= 1000){
		p <- p + geom_line(alpha = 0.8, aes(time, value, group=variable, colour=variable))
	} else {
		p <- p + geom_line(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + facet_grid(type ~ ., scales = "free_y")
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "RChar (KiBytes/s)\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p
	
	ggsave(file="rchars.png", width=12, height=6, dpi=100)
}

if(file.exists("readbytes_reduced.txt")){
	df <- read.table("readbytes_reduced.txt", header = TRUE, check.names = FALSE)
	num_columns <- ncol(df) - 1
	df <- mean_max_min(num_columns, df)
	df$type <- 'Process'
	
	df2 <- read.table("readbytes_node_reduced.txt", header = TRUE, check.names = FALSE)
	df2 <- mean_max_min(num_columns, df2)
	df2$type <- 'Node'
	
	df <- rbind(df, df2)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df3)
	if (num_columns <= 1000){
		p <- p + geom_line(alpha = 0.8, aes(time, value, group=variable, colour=variable))
	} else {
		p <- p + geom_line(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + facet_grid(type ~ ., scales = "free_y")
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Read_bytes per process (KiBytes/s)\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p
	
	ggsave(file="readbytes.png", width=12, height=6, dpi=100)
}