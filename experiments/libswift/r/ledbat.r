library(ggplot2)
library(reshape)

ledbat_files <- list.files(pattern="*.cc")
for (k in 1:length(ledbat_files)) {
    df <- read.table(ledbat_files[k], header = TRUE, check.names = FALSE,  fill = TRUE)

    output <- unlist(strsplit(ledbat_files[k], "\\."))

    p <- ggplot(df, aes(x=time, y=window)) + geom_line()
    p <- p + theme(legend.position="top")
    p <- p + labs(x = "\nTime (Seconds)", y = "Window size\n", title = paste(output[1], "cc window"))
    p

    ggsave(file=paste(output[1], "_cc.png"), width=8, height=6, dpi=100)
}

