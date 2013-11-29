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
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Connections per peer\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file=paste("total_connections_", toString(i), ".png", sep = ''), width=8, height=6, dpi=100)
	i = i + 1
}

i = 1
while(file.exists(paste("sum_incomming_connections_", toString(i), "_reduced.txt", sep = ''))){
	df <- read.table(paste("sum_incomming_connections_", toString(i), "_reduced.txt", sep = ''), header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df <- subset(df, df$time == max(df$time))
	
	p <- ggplot(df, aes(x=value)) + theme_bw()
	p <- p + geom_density()
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nSum incomming connections", y = "Probability\n")
	p
	
	ggsave(file=paste("incomming_connections_", toString(i), ".png", sep = ''), width=8, height=6, dpi=100)
	i = i + 1
}

i = 1
while(file.exists(paste("bl_skip_", toString(i), "_reduced.txt", sep = ''))){
    df <- read.table(paste("bl_skip_", toString(i), "_reduced.txt", sep = ''), header = TRUE, check.names = FALSE)
    df <- melt(df, id="time")
    df <- subset(df, df$value > 0)
    
    p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
    p <- p + geom_step(data = df, alpha=0.5)
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
    df <- melt(df, id="time")
    df <- subset(df, df$value > 0)
    
    p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
    p <- p + geom_step(data = df, alpha=0.5)
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
	df <- melt(df, id="time")
	df <- subset(df, df$value > 0)
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_step(data = df, alpha=0.5)
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bloomfilter CPU wall time spend\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file=paste("bl_time_", toString(i), ".png", sep = ''), width=8, height=6, dpi=100)
	i = i + 1
}