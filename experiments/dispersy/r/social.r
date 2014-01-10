library(ggplot2)
library(reshape)

if(file.exists("_received_from.txt")){
	df <- read.table("_received_from.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id=c("churn", "type"))
	df$x <- paste(df$churn, df$type)
	
	p <- ggplot(df, aes(x, value, fill=variable)) + theme_bw()
	p <- p + geom_bar(stat="identity")
	p <- p + theme(legend.position="bottom")
	p <- p + labs(x = "\nType of Message", y = "Number received\n")
	p <- p + scale_fill_brewer(palette="Dark2", name="Received from")
	p
	
	ggsave(file="_received_from.png", width=8, height=6, dpi=100)
}


if(file.exists("_received_after.txt")){
	df <- read.table("_received_after.txt", header = TRUE, check.names = FALSE)
	df$took <- df$received - df$created
	df$identifier <- NULL
	df$created <- NULL
	df$received <- NULL
	df$replicas <- NULL
	
	df <- melt(df, id=c("churn"))
	df$x <- paste(df$churn, df$type)
	
	p <- ggplot(df, aes(churn, value, fill=variable)) + theme_bw()
	p <- p + geom_boxplot()
	p <- p + theme(legend.position="none")
	p <- p + scale_fill_brewer(palette="Dark2")
	p <- p + labs(x = "\nAverage SessionLength", y = "Delay between creating and\nreceiving message\n")
	p
	
	ggsave(file="_received_after.png", width=8, height=6, dpi=100)
}