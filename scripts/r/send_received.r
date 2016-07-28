library(ggplot2)
library(reshape)
library(grid)
library(gridExtra)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

# Generates the send.png graph given the send_reduced.txt file
generate_send <- function(path, ylim) {
	df <- read.table(path, header = TRUE, check.names = FALSE, na.strings = "?")
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
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage (KiBytes total upload)\n")
	p <- p + xlim(minX, maxX)
	if(!is.null(ylim)){
		p <- p + ylim(0, ylim)
	}
	return(p)
}

current_send_path <- "send_reduced.txt"
upstream_send_path <- "../upstream/output/send_reduced.txt"

if(file.exists(current_send_path)){
	# If we have an upstream version, we are going to make a side comparison graph
	if(file.exists(upstream_send_path)){
		t1 <- read.table(current_send_path, header = TRUE, check.names = FALSE, na.strings = "?")
		t2 <- read.table(upstream_send_path, header = TRUE, check.names = FALSE, na.strings = "?")

		subdf <- t1[,2:ncol(t1)]
		subdf[] <- lapply(subdf, function(x) x/1024.0)
		max1 <- max(subdf)

		subdf <- t2[,2:ncol(t1)]
		subdf[] <- lapply(subdf, function(x) x/1024.0)
		max2 <- max(subdf)

		y_max <- max(max1, max2)

		current_send <- generate_send(current_send_path, y_max)
		upstream_send <- generate_send(upstream_send_path, y_max)

		ggsave(file="send.png", arrangeGrob(upstream_send, current_send, ncol=2), width=18, height=6, dpi=100)
	} else { # If not, we will just save this graph as-is.
		current_send <- generate_send(current_send_path, NULL)
		current_send
		ggsave(file="send.png", width=8, height=6, dpi=100)
	}
}

generate_received <- function(path, ylim) {
	df <- read.table("received_reduced.txt", header = TRUE, check.names = FALSE, na.strings = "?")
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
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage (KiBytes total download)\n")
	p <- p + xlim(minX, maxX)
	if(!is.null(ylim)){
		p <- p + ylim(0, ylim)
	}
	return(p)
}

current_received_path <- "received_reduced.txt"
upstream_received_path <- "../upstream/output/received_reduced.txt"

if(file.exists("received_reduced.txt")){
	# If we have an upstream version, we are going to make a side comparison graph
	if(file.exists(upstream_received_path)){
		t1 <- read.table(current_received_path, header = TRUE, check.names = FALSE, na.strings = "?")
		t2 <- read.table(upstream_received_path, header = TRUE, check.names = FALSE, na.strings = "?")

		subdf <- t1[,2:ncol(t1)]
		subdf[] <- lapply(subdf, function(x) x/1024.0)
		max1 <- max(subdf)

		subdf <- t2[,2:ncol(t1)]
		subdf[] <- lapply(subdf, function(x) x/1024.0)
		max2 <- max(subdf)

		y_max <- max(max1, max2)

		current_received <- generate_send(current_received_path, y_max)
		upstream_received <- generate_send(upstream_received_path, y_max)

		ggsave(file="send.png", arrangeGrob(upstream_received, current_received, ncol=2), width=18, height=6, dpi=100)
	} else { # If not, we will just save this graph as-is.
		current_send <- generate_send(current_received_path, NULL)
		current_send
		ggsave(file="send.png", width=8, height=6, dpi=100)
	}
}
