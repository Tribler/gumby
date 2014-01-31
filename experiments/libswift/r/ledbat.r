library(ggplot2)
library(reshape)

if (file.exists("seeder.cc")) {
    df <- read.table("seeder.cc", header = TRUE, check.names = FALSE,  fill = TRUE)

    p <- ggplot(df, aes(x=time, y=window)) + geom_line()
    p <- p + theme(legend.position="top")
    p <- p + labs(x = "\nTime (Seconds)", y = "Window size\n", title="Ledbat window")
    p

    ggsave(file="seeder_cc.png", width=8, height=6, dpi=100)
}

