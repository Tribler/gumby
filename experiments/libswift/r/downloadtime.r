library(ggplot2)
library(reshape)

stderr_files <- list.files(pattern="*.err")
for (k in 1:length(stderr_files)) {
    df <- read.table(stderr_files[k], header = TRUE, check.names = FALSE)
    df$percent <- NULL
    df <- melt(df, id=c("time"))

    p <- ggplot(df, aes(x=time, y=value, fill=variable))
    p <- p + geom_line(alpha = 0.8, aes(time, value, group=variable, colour=variable))
    p <- p + theme(legend.position="top")
    p <- p + labs(x = "\nTime (Seconds)", y = "Speed (KByte/s)\n")
    p

    output <- unlist(strsplit(stderr_files[k], "\\."))
    ggsave(file=paste(output[1], ".png"), width=8, height=6, dpi=100)
}

