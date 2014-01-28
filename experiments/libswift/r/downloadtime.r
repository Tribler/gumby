library(ggplot2)
library(reshape)

if(file.exists("stderr.data")){
    df <- read.table("stderr.data", header = TRUE, check.names = FALSE)

    p <- ggplot(df, aes(x=time, y=dlspeed))
    p <- p + geom_line()
    p

    ggsave(file="speed.png", width=8, height=6, dpi=100)
}


