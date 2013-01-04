.libPaths( c("~/R/x86_64-redhat-linux-gnu-library/2.15", .libPaths()))
is.installed <- function(mypkg) is.element(mypkg, installed.packages()[,1]) 

toInstall <- c("ggplot2", "reshape")
for (package in toInstall){
	if (is.installed(package) == FALSE){
		install.packages(package, repos = "http://cran.r-project.org", lib="~/R/x86_64-redhat-linux-gnu-library/2.15")		
	}
}
lapply(toInstall, library, character.only = TRUE)
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
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage (KiBytes total upload)")
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
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage (KiBytes total download)")
	p
	ggsave(file="received.png", width=8, height=6, dpi=100)
}