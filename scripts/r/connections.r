library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

if(file.exists("annotations.txt")){
	df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
	show_mean <- length(colnames(df2)) != 3
	df2 <- melt(df2)
	df2 <- ddply(df2, .(annotation), summarise, meanx = mean(value), minx = min(value), maxx = max(value))
	df2$linesize <- max((df2$maxx - df2$minx) / 2, 1)
	df2$linepos <- df2$minx + df2$linesize
}

i = 1
while(file.exists(paste("total_connections_", toString(i), "_reduced.txt", sep = ''))){
	df <- read.table(paste("total_connections_", toString(i), "_reduced.txt", sep = ''), header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	
	p <- ggplot(df) + theme_bw()
	
	if(file.exists("annotations.txt")){
		p <- p + stat_vline(alpha = 0.2, data=df2, xintercept = df2$linepos, size = df2$linesize, mapping = aes(colour=annotation))
		p <- p + geom_text(alpha = 0.4, data=df2, angle = 90, aes(x=maxx, y=max(df$value), label=annotation, hjust=1, size=6))
		if (show_mean) {
			p <- p + stat_vline(alpha = 0.6, data=df2, xintercept = df2$meanx, size = 1, mapping = aes(colour=annotation))
		}
	}
	
	p <- p + geom_step(data = df, alpha = 0.8, aes(time, value, group=variable, colour=variable))
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
	df <- subset(df, df$time == max(df$time))
	df <- melt(df, id="time")
	
	p <- ggplot(df, aes(x=value)) + theme_bw()
	
	if(file.exists("annotations.txt")){
		p <- p + stat_vline(alpha = 0.2, data=df2, xintercept = df2$linepos, size = df2$linesize, mapping = aes(colour=annotation))
		p <- p + geom_text(alpha = 0.4, data=df2, angle = 90, aes(x=maxx, y=max(df$value), label=annotation, hjust=1, size=6))
		if (show_mean) {
			p <- p + stat_vline(alpha = 0.6, data=df2, xintercept = df2$meanx, size = 1, mapping = aes(colour=annotation))
		}
	}
	
	p <- p + geom_density()
	p <- p + geom_histogram(aes(y=..density.., alpha=0.8))
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nSum incomming connections", y = "Density\n")
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
	
	if(file.exists("annotations.txt")){
		p <- p + stat_vline(alpha = 0.2, data=df2, xintercept = df2$linepos, size = df2$linesize, mapping = aes(colour=annotation))
		p <- p + geom_text(alpha = 0.4, data=df2, angle = 90, aes(x=maxx, y=max(df$value), label=annotation, hjust=1, size=6))
		if (show_mean) {
			p <- p + stat_vline(alpha = 0.6, data=df2, xintercept = df2$meanx, size = 1, mapping = aes(colour=annotation))
		}
	}
	
    p <- p + geom_step(data = df, alpha=0.8)
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
	
	if(file.exists("annotations.txt")){
		p <- p + stat_vline(alpha = 0.2, data=df2, xintercept = df2$linepos, size = df2$linesize, mapping = aes(colour=annotation))
		p <- p + geom_text(alpha = 0.4, data=df2, angle = 90, aes(x=maxx, y=max(df$value), label=annotation, hjust=1, size=6))
		if (show_mean) {
			p <- p + stat_vline(alpha = 0.6, data=df2, xintercept = df2$meanx, size = 1, mapping = aes(colour=annotation))
		}
	}
	
    p <- p + geom_step(data = df, alpha=0.8)
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
	
	if(file.exists("annotations.txt")){
		p <- p + stat_vline(alpha = 0.2, data=df2, xintercept = df2$linepos, size = df2$linesize, mapping = aes(colour=annotation))
		p <- p + geom_text(alpha = 0.4, data=df2, angle = 90, aes(x=maxx, y=max(df$value), label=annotation, hjust=1, size=6))
		if (show_mean) {
			p <- p + stat_vline(alpha = 0.6, data=df2, xintercept = df2$meanx, size = 1, mapping = aes(colour=annotation))
		}
	}
	
	p <- p + geom_step(data = df, alpha=0.8)
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bloomfilter CPU wall time spend\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file=paste("bl_time_", toString(i), ".png", sep = ''), width=8, height=6, dpi=100)
	i = i + 1
}