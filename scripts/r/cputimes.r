library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

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
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_line(data = df, alpha = 0.5)
	
	if(file.exists("utimes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}
	 
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Utime\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="utimes.png", width=8, height=6, dpi=100)
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
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_line(data = df, alpha = 0.5)
	
	if(file.exists("stimes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}
	 
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Stime\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="stimes.png", width=8, height=6, dpi=100)
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
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_line(data = df, alpha = 0.5)
	
	if(file.exists("wchars_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}
	 
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "WChar per process (KiBytes/s)\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="wchars.png", width=8, height=6, dpi=100)
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
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_line(data = df, alpha = 0.5)
	
	if(file.exists("rchars_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}
		 
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "RChar (KiBytes/s)\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="rchars.png", width=8, height=6, dpi=100)
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
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_line(data = df, alpha = 0.5)
	
	if(file.exists("writebytes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}
	 
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Write_bytes per process (KiBytes/s)\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="writebytes.png", width=8, height=6, dpi=100)
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
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_line(data = df, alpha = 0.5)
	
	if(file.exists("readbytes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}
	 
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Read_bytes per process (KiBytes/s)\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="readbytes.png", width=8, height=6, dpi=100)
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
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_step(data = df, alpha = 0.5)
	
	if(file.exists("vsizes_node_reduced.txt")){
		p <- p + facet_grid(type ~ ., scales = "free_y")
	}
	 
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "VSize (KiBytes)\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="vsizes.png", width=8, height=6, dpi=100)
}