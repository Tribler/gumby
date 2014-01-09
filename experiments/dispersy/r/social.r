library(ggplot2)
library(reshape)

if(file.exists("_received_from.txt")){
    df <- read.table("_received_from.txt", header = TRUE, check.names = FALSE)
    df <- melt(df, id=c("churn", "type"))
    df$x <- paste(df$churn, df$type)
    
    p <- ggplot(df, aes(x, value, fill=variable, colour=variable)) + theme_bw()
    p <- p + geom_bar(stat="identity")
    p <- p + theme(legend.position="none")
    p <- p + labs(x = "\nType of Message", y = "Number received\n")
    p
    
    ggsave(file="_received_from.png", width=8, height=6, dpi=100)
}