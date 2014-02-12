library(ggplot2)
library(reshape)

if (file.exists("leecher.cc") && file.exists("leecher.cc")) {
    df <- read.table("leecher.cc", header = TRUE, check.names = FALSE,  fill = TRUE)

    p <- ggplot(df, aes(x=time, y=dip)) + geom_line()
    p <- p + labs(x = "\nTime (Seconds)", y = "Dip\n")
    p

    ggsave(file="dip.png", width=8, height=6, dpi=100)
}

