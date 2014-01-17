library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

i = 1
while(file.exists(paste("bl_skip_", toString(i), "_reduced.txt", sep = ''))){
	df <- read.table(paste("bl_skip_", toString(i), "_reduced.txt", sep = ''), header = TRUE, check.names = FALSE)
	num_columns <- ncol(df) - 1
	df <- mean_max_min(num_columns, df)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df2)
	if (num_columns <= 1000){
		p <- p + geom_step(data = df, alpha=0.8, aes(time, value, group=variable, colour=variable))
	} else {
		p <- p + geom_step(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bloomfilter skips\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file=paste("bl_skip_", toString(i), ".png", sep = ''), width=8, height=6, dpi=100)
	i = i + 1
}

i = 1
while(file.exists(paste("bl_reuse_", toString(i), "_reduced.txt", sep = ''))){
	df <- read.table(paste("bl_reuse_", toString(i), "_reduced.txt", sep = ''), header = TRUE, check.names = FALSE)
	num_columns <- ncol(df) - 1
	df <- mean_max_min(num_columns, df)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df2)
	
	if (num_columns <= 1000){
		p <- p + geom_step(data = df, alpha=0.8, aes(time, value, group=variable, colour=variable))
	} else {
		p <- p + geom_step(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bloomfilter reuse\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file=paste("bl_reuse_", toString(i), ".png", sep = ''), width=8, height=6, dpi=100)
	i = i + 1
}

i = 1
while(file.exists(paste("bl_time_", toString(i), "_reduced.txt", sep = ''))){
	df <- read.table(paste("bl_time_", toString(i), "_reduced.txt", sep = ''), header = TRUE, check.names = FALSE)
	num_columns <- ncol(df) - 1
	
	df <- mean_max_min(num_columns, df)
	
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df2)
	if (num_columns <= 1000){
		p <- p + geom_step(data = df, alpha=0.8, aes(time, value, group=variable, colour=variable))
	} else {
		p <- p + geom_step(aes(time, mean), colour = '2')
		p <- p + geom_ribbon(alpha = 0.3, aes(time, mean, ymin=min, ymax=max, linetype=NA))
		p <- p + geom_ribbon(alpha = 0.3, aes(time, ymin=Q1, ymax=Q3, linetype=NA))
	}
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bloomfilter CPU wall time spend\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file=paste("bl_time_", toString(i), ".png", sep = ''), width=8, height=6, dpi=100)
	i = i + 1
}