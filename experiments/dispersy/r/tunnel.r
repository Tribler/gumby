library(ggplot2)
library(reshape2)
library(stringr)
library(plyr)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()
print(df2)


if(file.exists("speed_download_reduced.txt")){
	df <- read.table("speed_download_reduced.txt", header = TRUE, check.names = FALSE, na.strings = "?")
	num_columns <- ncol(df) - 1
	
	subdf <- df[,2:ncol(df)]
	subdf[] <- lapply(subdf, function(x) x/1024.0)
	df <- cbind(df['time'], subdf)
	df <- mean_max_min(num_columns, df)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	if (num_columns <= 1000){
		p <- p + geom_line(alpha = 0.8, aes(time, value, group=variable, colour=variable))
	} else {
		p <- p + geom_line(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Hidden seeding (KiBytes download)\n")
	p <- p + xlim(minX, maxX)
	p
	ggsave(file="speed_download.png", width=8, height=6, dpi=100)
}

if(file.exists("speed_upload_reduced.txt")){
	df <- read.table("speed_upload_reduced.txt", header = TRUE, check.names = FALSE, na.strings = "?")
	num_columns <- ncol(df) - 1
	
	subdf <- df[,2:ncol(df)]
	subdf[] <- lapply(subdf, function(x) x/1024.0)
	df <- cbind(df['time'], subdf)
	df <- mean_max_min(num_columns, df)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	if (num_columns <= 1000){
		p <- p + geom_line(alpha = 0.8, aes(time, value, group=variable, colour=variable))
	} else {
		p <- p + geom_line(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Hidden seeding (KiBytes upload)\n")
	p <- p + xlim(minX, maxX)
	p
	ggsave(file="speed_upload.png", width=8, height=6, dpi=100)
}

if(file.exists("progress_percentage_reduced.txt")){
	df <- read.table("progress_percentage_reduced.txt", header = TRUE, check.names = FALSE, na.strings = "?")
	num_columns <- ncol(df) - 1
	
	subdf <- df[,2:ncol(df)]
	subdf[] <- lapply(subdf, function(x) x/1024.0)
	df <- cbind(df['time'], subdf)
	df <- mean_max_min(num_columns, df)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	if (num_columns <= 1000){
		p <- p + geom_line(alpha = 0.8, aes(time, value, group=variable, colour=variable))
	} else {
		p <- p + geom_line(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Download progress (%)\n")
	p <- p + xlim(minX, maxX)
	p
	ggsave(file="progress_percentage.png", width=8, height=6, dpi=100)
}
