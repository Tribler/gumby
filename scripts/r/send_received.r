library(ggplot2)
library(reshape)
library(grid)
library(gridExtra)

R.Version()

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

# Load the comparison function
source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'side_comparison.r', sep='/'))

# Generates the send.png graph given the send_reduced.txt file
generate_send <- function(path) {
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
	return(p)
}

current_send_path <- "send_reduced.txt"
upstream_send_path <- "../upstream/output/send_reduced.txt"

if(file.exists(current_send_path)){
	# If we have an upstream version, we are going to make a side comparison graph
	if(file.exists(upstream_send_path)){
		current_send <- generate_send(current_send_path)
		upstream_send <- generate_send(upstream_send_path)

        create_comparison(upstream_send, current_send, "send.png")
	} else { # If not, we will just save this graph as-is.
		current_send <- generate_send(current_send_path, NULL)
		current_send
		ggsave(file="send.png", width=8, height=6, dpi=100)
	}
}

generate_received <- function(path) {
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
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage (KiBytes total download)\n")
	p <- p + xlim(minX, maxX)
	return(p)
}

current_received_path <- "received_reduced.txt"
upstream_received_path <- "../upstream/output/received_reduced.txt"

if(file.exists(current_received_path)){
	# If we have an upstream version, we are going to make a side comparison graph
	if(file.exists(upstream_received_path)){
		current_received <- generate_received(current_received_path)
		upstream_received <- generate_received(upstream_received_path)

        create_comparison(upstream_received, current_received, "received.png")
	} else { # If not, we will just save this graph as-is.
		current_received <- generate_received(current_received_path, NULL)
		current_received
		ggsave(file="received.png", width=8, height=6, dpi=100)
	}
}
