library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

if(file.exists("send_diff_reduced.txt")){
	df <- read.table("send_diff_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df <- subset(df, df$value > 0)
	df$value = df$value/1024.0
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_point(data = df, aes(size=value), alpha=0.5)
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage for peer (KiBytes/s upload)\n")
	p <- p + xlim(minX, maxX)
	p
	ggsave(file="send_diff.png", width=8, height=6, dpi=100)
}

if(file.exists("received_diff_reduced.txt")){
	df <- read.table("received_diff_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df <- subset(df, df$value > 0)
	df$value = df$value/1024.0
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_point(data = df, aes(size=value), alpha=0.5)
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage for peer (KiBytes/s download)\n")
	p <- p + xlim(minX, maxX)
	p
	ggsave(file="received_diff.png", width=8, height=6, dpi=100)
}

if(file.exists("send_reduced.txt")){
	df <- read.table("send_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df$value = df$value/1024.0
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_line(alpha = 5/10)
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage (KiBytes total upload)\n")
	p <- p + xlim(minX, maxX)
	p
	ggsave(file="send.png", width=8, height=6, dpi=100)
}

if(file.exists("received_reduced.txt")){
	df <- read.table("received_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df$value = df$value/1024.0
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_line(alpha = 5/10)
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage (KiBytes total download)\n")
	p <- p + xlim(minX, maxX)
	p
	ggsave(file="received.png", width=8, height=6, dpi=100)
}

if(file.exists("bl_skip_reduced.txt")){
    df <- read.table("bl_skip_reduced.txt", header = TRUE, check.names = FALSE)
    df <- melt(df, id="time")
    df <- subset(df, df$value > 0)
    
    p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
    p <- p + geom_point(data = df, aes(size=value), alpha=0.5)
    p <- p + opts(legend.position="none")
    p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bloomfilter skips\n")
    p <- p + xlim(minX, maxX)
    p
    ggsave(file="bl_skip.png", width=8, height=6, dpi=100)
}

if(file.exists("bl_reuse_reduced.txt")){
    df <- read.table("bl_reuse_reduced.txt", header = TRUE, check.names = FALSE)
    df <- melt(df, id="time")
    df <- subset(df, df$value > 0)
    
    p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
    p <- p + geom_point(data = df, aes(size=value), alpha=0.5)
    p <- p + opts(legend.position="none")
    p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bloomfilter reuse\n")
    p <- p + xlim(minX, maxX)
    p
    ggsave(file="bl_reuse.png", width=8, height=6, dpi=100)
}