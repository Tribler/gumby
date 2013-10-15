library(ggplot2)
library(reshape)

args <- commandArgs(TRUE)
minX <- as.integer(args[1])
maxX <- as.integer(args[2])

if(file.exists("utimes_reduced.txt")){
	df <- read.table("utimes_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df$type <- 'Process'

	if(file.exists("utimes_node_reduced.txt")){
		df2 <- read.table("utimes_node_reduced.txt", header = TRUE, check.names = FALSE)
		df2 <- melt(df2, id="time")
		df2$type <- 'Node'

		df <- rbind(df, df2)
	}

	p <- ggplot(df) + theme_bw()

	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
		p <- p + geom_vline(alpha = 0.3, data=df2, aes(xintercept = time))
		p <- p + geom_text(alpha = 0.3, data=df2, angle = 90, aes(x=time, y=max(df$value), label=remark, hjust=1, vjust=start, size=3))
	}

	p <- p + geom_line(aes(time, value, group=variable, colour=variable))

	if(file.exists("utimes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}

	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Utime\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p

	ggsave(file="utimes.png", width=12, height=6, dpi=100)
}

if(file.exists("stimes_reduced.txt")){
	df <- read.table("stimes_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df$type <- 'Process'

	if(file.exists("stimes_node_reduced.txt")){
		df2 <- read.table("stimes_node_reduced.txt", header = TRUE, check.names = FALSE)
		df2 <- melt(df2, id="time")
		df2$type <- 'Node'

		df <- rbind(df, df2)
	}

	p <- ggplot(df) + theme_bw()

	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
		p <- p + geom_vline(alpha = 0.3, data=df2, aes(xintercept = time))
		p <- p + geom_text(alpha = 0.3, data=df2, angle = 90, aes(x=time, y=max(df$value), label=remark, hjust=1, vjust=start, size=3))
	}

	p <- p + geom_line(aes(time, value, group=variable, colour=variable))

	if(file.exists("stimes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}

	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Stime\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p

	ggsave(file="stimes.png", width=12, height=6, dpi=100)
}

if(file.exists("wchars_reduced.txt")){
	df <- read.table("wchars_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df$type <- 'Process'

	if(file.exists("wchars_node_reduced.txt")){
		df2 <- read.table("wchars_node_reduced.txt", header = TRUE, check.names = FALSE)
		df2 <- melt(df2, id="time")
		df2$type <- 'Node'

		df <- rbind(df, df2)
	}

	p <- ggplot(df) + theme_bw()

	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
		p <- p + geom_vline(alpha = 0.3, data=df2, aes(xintercept = time))
		p <- p + geom_text(alpha = 0.3, data=df2, angle = 90, aes(x=time, y=max(df$value), label=remark, hjust=1, vjust=start, size=3))
	}

	p <- p + geom_line(aes(time, value, group=variable, colour=variable))

	if(file.exists("wchars_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}

	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "WChar per process (KiBytes/s)\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p

	ggsave(file="wchars.png", width=12, height=6, dpi=100)
}

if(file.exists("rchars_reduced.txt")){
	df <- read.table("rchars_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df$type <- 'Process'

	if(file.exists("rchars_node_reduced.txt")){
		df2 <- read.table("rchars_node_reduced.txt", header = TRUE, check.names = FALSE)
		df2 <- melt(df2, id="time")
		df2$type <- 'Node'

		df <- rbind(df, df2)
	}

	p <- ggplot(df) + theme_bw()

	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
		p <- p + geom_vline(alpha = 0.3, data=df2, aes(xintercept = time))
		p <- p + geom_text(alpha = 0.3, data=df2, angle = 90, aes(x=time, y=max(df$value), label=remark, hjust=1, vjust=start, size=3))
	}

	p <- p + geom_line(aes(time, value, group=variable, colour=variable))

	if(file.exists("rchars_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}

	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "RChar (KiBytes/s)\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p

	ggsave(file="rchars.png", width=12, height=6, dpi=100)
}

if(file.exists("writebytes_reduced.txt")){
	df <- read.table("writebytes_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df$type <- 'Process'

	if(file.exists("writebytes_node_reduced.txt")){
		df2 <- read.table("writebytes_node_reduced.txt", header = TRUE, check.names = FALSE)
		df2 <- melt(df2, id="time")
		df2$type <- 'Node'

		df <- rbind(df, df2)
	}

	p <- ggplot(df) + theme_bw()

	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
		p <- p + geom_vline(alpha = 0.3, data=df2, aes(xintercept = time))
		p <- p + geom_text(alpha = 0.3, data=df2, angle = 90, aes(x=time, y=max(df$value), label=remark, hjust=1, vjust=start, size=3))
	}

	p <- p + geom_line(aes(time, value, group=variable, colour=variable))

	if(file.exists("writebytes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}

	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Write_bytes per process (KiBytes/s)\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p

	ggsave(file="writebytes.png", width=12, height=6, dpi=100)
}

if(file.exists("readbytes_reduced.txt")){
	df <- read.table("readbytes_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df$type <- 'Process'

	if(file.exists("readbytes_node_reduced.txt")){
		df2 <- read.table("readbytes_node_reduced.txt", header = TRUE, check.names = FALSE)
		df2 <- melt(df2, id="time")
		df2$type <- 'Node'

		df <- rbind(df, df2)
	}

	p <- ggplot(df) + theme_bw()

	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
		p <- p + geom_vline(alpha = 0.3, data=df2, aes(xintercept = time))
		p <- p + geom_text(alpha = 0.3, data=df2, angle = 90, aes(x=time, y=max(df$value), label=remark, hjust=1, vjust=start, size=3))
	}

	p <- p + geom_line(aes(time, value, group=variable, colour=variable))

	if(file.exists("readbytes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}

	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Read_bytes per process (KiBytes/s)\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p

	ggsave(file="readbytes.png", width=12, height=6, dpi=100)
}

if(file.exists("vsizes_reduced.txt")){
	df <- read.table("vsizes_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df$type <- 'Process'

	if(file.exists("vsizes_node_reduced.txt")){
		df2 <- read.table("vsizes_node_reduced.txt", header = TRUE, check.names = FALSE)
		df2 <- melt(df2, id="time")
		df2$type <- 'Node'

		df <- rbind(df, df2)
	}

	p <- ggplot(df) + theme_bw()

	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
		p <- p + geom_vline(alpha = 0.3, data=df2, aes(xintercept = time))
		p <- p + geom_text(alpha = 0.3, data=df2, angle = 90, aes(x=time, y=max(df$value), label=remark, hjust=1, vjust=start, size=3))
	}

	p <- p + geom_step(aes(time, value, group=variable, colour=variable))

	if(file.exists("vsizes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}

	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "VSize (MBytes)\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p

	ggsave(file="vsizes.png", width=12, height=6, dpi=100)
}
