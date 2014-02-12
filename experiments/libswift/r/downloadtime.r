library(ggplot2)
library(reshape)

stderr_files <- list.files(pattern="*.err")
for (k in 1:length(stderr_files)) {
    df <- read.table(stderr_files[k], header = TRUE, check.names = FALSE)
    df$percent <- NULL
    df <- melt(df, id=c("time"))

    output <- unlist(strsplit(stderr_files[k], "\\."))

    p <- ggplot(df, aes(x=time, y=value, fill=variable))
    p <- p + geom_line(alpha = 0.8, aes(time, value, group=variable, colour=variable))
    p <- p + theme(legend.position="top", legend.title=element_blank())
    p <- p + labs(x = "\nTime (Seconds)", y = "Speed (KByte/s)\n", title = paste(output[1], "network speeds"))
    p

    ggsave(file=paste(output[1], "speed.png", sep = "_"), width=8, height=6, dpi=100)

}

for (k in 1:length(stderr_files)) {
 
    df <- read.table(stderr_files[k], header = TRUE, check.names = FALSE)
    df$upload <- NULL
    df$download <- NULL

    output <- unlist(strsplit(stderr_files[k], "\\."))

    p <- ggplot(df, aes(x=time, y=percent))
    p <- p + geom_line() + ylim(0,100)
    p <- p + theme(legend.position="top", legend.title=element_blank())
    p <- p + labs(x = "\nTime (Seconds)", y = "Completion (Percent %)\n", title = paste(output[1], "Completion"))
    p

    ggsave(file=paste(output[1], "complete.png", sep = "_"), width=8, height=6, dpi=100)

}
