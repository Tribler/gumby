library(ggplot2)
library(reshape)

df <- read.table("sum_total_records.txt", header = TRUE, check.names = FALSE)
df <- melt(df, id="time")

p <- ggplot(df, aes(time, value, group=variable, colour=type, linetype=type)) + theme_bw()
p <- p + geom_line(data = df, alpha = 0.5)
p <- p + opts(legend.position="none")
p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages received by peer\n")
p

ggsave(file="total_records.png")